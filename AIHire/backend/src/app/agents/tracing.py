# LLM 可观测性的"记账员"：trace_llm_call 装饰器包住每次 LLM 调用，
#   自动记录输入输出、token 估算、耗时，写入 llm_call_logs 表（可选同步 Langfuse）。
"""LLM 调用链路追踪 — @trace_llm_call 装饰器

使用方式：
    @trace_llm_call(function_name="resume_analyze")
    async def chat(self, system, messages, ...):
        ...

自动记录：
    - 调用时间、功能名称、模型
    - 请求内容（system prompt + messages）
    - 响应内容
    - Token 用量（根据文本粗略估算）
    - 延迟（毫秒）
"""
import time  # Python 标准库：记录调用开始、结束的时间，用于计算耗时。
import logging  # Python 标准库：输出追踪模块自身的运行日志。
import asyncio  # Python 标准库：创建异步任务，让日志写入独立执行。
from functools import wraps  # 保留被装饰函数的名称、说明等信息。
from typing import Optional, Callable  # Optional 表示允许 None；Callable 表示可调用对象，例如函数。

logger = logging.getLogger(__name__)  # 使用当前模块名创建日志记录器，便于定位日志来源。

# ===== Langfuse：可选的模型调用观测平台 =====
_langfuse_client = None  # 缓存可复用的 Langfuse 客户端；None 表示尚未取得客户端。
_langfuse_checked = False  # 是否已经尝试初始化；无论成功、关闭还是失败，都只尝试一次。


def _get_langfuse():
    """懒加载 Langfuse 客户端；未启用或导入失败返回 None（只尝试一次，避免重复报错）"""
    global _langfuse_client, _langfuse_checked  # 修改模块级变量，而不是创建同名局部变量。
    if _langfuse_checked:
        return _langfuse_client
    _langfuse_checked = True
    try:
        from app.config import settings
        if not settings.LANGFUSE_ENABLED:
            return None
        from langfuse import Langfuse  # 第三方可选依赖：启用时才导入，未安装会由 except 捕获。
        _langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        logger.info("Langfuse 已启用: %s", settings.LANGFUSE_HOST)
    except Exception as e:
        logger.warning("Langfuse 初始化失败（本次运行不再尝试）: %s", e)
        _langfuse_client = None
    return _langfuse_client

# 保存调用方传入的会话引用；这是模块级普通变量，不是请求隔离的上下文变量。
# 原写日志函数使用独立会话，并不读取这个引用。
_trace_db_session = None


def set_trace_db_session(session):
    """保存调用方传入的数据库会话引用；当前写日志函数不使用它。"""
    global _trace_db_session
    _trace_db_session = session


async def _write_log_async(function_name: str, model: str,
                           system_prompt: str, messages: list,
                           response: str, prompt_tokens: int,
                           completion_tokens: int, total_tokens: int,
                           latency_ms: float, session_id: Optional[str] = None):
    """异步写 LLM 调用日志到数据库

    使用独立的数据库会话，避免影响主流程事务。
    """
    try:
        from app.database import async_session_factory
        from app.models.llm_log import LLMCallLog

        # 独立事务：主业务的提交或回滚不会直接决定这条日志的提交。
        async with async_session_factory() as db:
            log = LLMCallLog(
                function_name=function_name,
                model=model,
                system_prompt=str(system_prompt)[:500] if system_prompt else None,  # 系统提示词最多保存 500 个字符。
                messages=messages,
                response=str(response)[:2000] if response else None,  # 响应最多保存 2000 个字符。
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=round(latency_ms, 2),  # 毫秒耗时保留两位小数。
                session_id=session_id,  # 用于关联调用；装饰器未传入时为 None。
            )
            db.add(log)  # 将日志对象加入会话。
            await db.commit()  # 提交后才真正完成数据库写入。
        # Langfuse 追踪上报（可选，失败不影响主流程）
        # v3 SDK 手动埋点：start_span 建 trace → update_trace 关联会话 → start_generation 记录 LLM 调用
        try:
            lf = _get_langfuse()
            if lf is not None:
                trace_id = lf.create_trace_id()  # 为这次调用创建追踪编号。
                span = lf.start_span(  # span 表示一次可记录起止时间的操作。
                    name=function_name,
                    trace_context={"trace_id": trace_id},  # 指定这次操作所属的追踪。
                    metadata={"model": model, "latency_ms": round(latency_ms, 2)},  # 附带模型与耗时信息。
                )
                span.update_trace(session_id=session_id, name=function_name)
                gen = span.start_generation(  # generation 专门记录模型生成的输入、输出和用量。
                    name=function_name,
                    model=model,
                    input={"system": system_prompt, "messages": messages},  # 上报完整输入，不使用数据库截断值。
                    output=response,  # 上报完整响应。
                    usage_details={  # Token 估算值：输入、输出、合计。
                        "input": prompt_tokens,
                        "output": completion_tokens,
                        "total": total_tokens,
                    },
                )
                gen.end()
                span.end()
                lf.flush()  # 同步上报 SDK 缓冲的数据；这一步可能占用事件循环时间。
        except Exception as lf_err:
            logger.debug("Langfuse 导出失败（非关键）: %s", lf_err)
    except Exception as e:
        # 日志写入失败不影响主流程
        logger.warning(f"LLM trace 写入失败（非关键）: {e}")


def trace_llm_call(function_name: str = "unknown"):
    """LLM 调用追踪装饰器

    装饰 llm_client.chat() 方法，自动记录调用的输入输出、token用量、延迟。

    Args:
        function_name: 功能名称，用于区分调用来源（如 "resume_analyze" / "rag_chat"）
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, system: str, messages: list,
                          response_format=None,
                          temperature: float = 0.1,
                          max_tokens: int = 4096, **kwargs):
            start_time = time.time()  # 当前时间戳，单位为秒；保持原项目计时方式。
            model_name = getattr(self, '_model_name', 'unknown')  # 读取客户端模型名，属性不存在时使用 unknown。

            # self 是客户端实例；system 是系统提示词；messages 是对话消息列表。
            # response_format 是响应格式，temperature 控制生成随机性，max_tokens 是生成上限。
            # **kwargs 接收其他关键字参数，并原样交给被装饰的方法。
            # 执行原始调用
            try:
                response = await func(self, system, messages,
                                      response_format=response_format,
                                      temperature=temperature,
                                      max_tokens=max_tokens, **kwargs)
                latency = (time.time() - start_time) * 1000
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                # 即使失败也安排后台日志任务；Token 记为 0，并继续抛出原异常。
                asyncio.create_task(_write_log_async(
                    function_name=function_name,
                    model=model_name,
                    system_prompt=system,
                    messages=messages,
                    response=f"ERROR: {str(e)}",
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=latency,
                ))
                raise

            # 按文本粗略估算 Token，并非模型服务返回的精确用量。
            combined_prompt = f"System: {system}\nMessages: {messages}"
            prompt_tokens = _estimate_tokens(combined_prompt)
            completion_tokens = _estimate_tokens(response)
            total_tokens = prompt_tokens + completion_tokens

            # 创建后台任务，不等待数据库写入结束；程序提前退出时日志可能来不及写入。
            asyncio.create_task(_write_log_async(
                function_name=function_name,
                model=model_name,
                system_prompt=system,
                messages=messages,
                response=response,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency,
            ))

            return response
        return wrapper
    return decorator


def _estimate_tokens(text) -> int:
    """粗略估算 token 数量（中文约 1.5 字符/token，英文约 4 字符/token）

    不需要精确计算，用于相对比较即可。
    """
    if isinstance(text, list):
        text = str(text)
    if not isinstance(text, str):
        text = str(text)
    # 粗略估计：中文1.5字/token，英文4字/token
    chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')  # 统计这个字符范围内的汉字。
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4) or 1  # 取整；结果为 0 时返回 1。
