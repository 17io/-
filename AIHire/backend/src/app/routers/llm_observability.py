# 查询大模型调用的输入输出、Token 用量和耗时，并提供聚合统计。
# 日志模型对应 llm_call_logs 表；本模块负责读取日志数据。
"""LLM 调用可观测性 API：查询调用日志和聚合统计。"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import LLMCallLog, UserRole  # 大模型调用日志模型，以及系统角色枚举。
from app.dependencies import require_role

router = APIRouter(
    prefix="/api/llm",  # 这组大模型调用日志接口共同的地址前缀。
    tags=["LLM可观测性"],  # 自动接口文档中的分组名称。
    dependencies=[Depends(require_role([UserRole.ADMIN, UserRole.HR]))],  # 整组接口只允许管理员或 HR 访问。
)


@router.get("/logs")
async def list_llm_logs(
    page: int = Query(1, ge=1, description="页码"),  # 默认第 1 页，不能小于 1。
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),  # 默认 20 条，最多 100 条。
    function_name: Optional[str] = Query(None, description="按功能名称过滤"),  # 可选查询参数，例如 resume_analyze；使用精确匹配。
    db: AsyncSession = Depends(get_db),
):
    """查询 LLM 调用日志（分页）"""
    query = select(LLMCallLog)  # 查询日志表；管理员和 HR 均可读取全局日志，不按候选人负责人过滤。

    if function_name:
        query = query.where(LLMCallLog.function_name == function_name)

    # 总数
    # subquery 将已经附带筛选条件的查询作为子查询；select_from 指定从它统计总行数。
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页查询（按时间倒序）
    query = query.order_by(LLMCallLog.timestamp.desc())  # 新调用记录排在前面。
    query = query.offset((page - 1) * page_size).limit(page_size)  # 跳过前面页的数据，再取本页条数。
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [log.to_dict() for log in logs],  # 使用模型的方法生成列表项，不包含 messages 和 response 正文。
    }


@router.get("/logs/{log_id}")
async def get_llm_log_detail(log_id: int, db: AsyncSession = Depends(get_db)):
    # log_id 是地址中的日志编号，例如 /api/llm/logs/12。
    """查询单条调用详情，返回数据库已保存的请求和响应内容。"""
    result = await db.execute(select(LLMCallLog).where(LLMCallLog.id == log_id))
    log = result.scalar_one_or_none()  # 取出唯一日志对象，找不到时为 None。
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="日志不存在")

    return {
        "id": log.id,
        "timestamp": log.timestamp.isoformat() if log.timestamp else "",  # 日期时间转为 ISO 格式字符串。
        "session_id": log.session_id,  # 关联会话编号，可以为空。
        "function_name": log.function_name,
        "model": log.model,
        "system_prompt": log.system_prompt,  # 数据库中保存的系统提示词。
        "messages": log.messages,  # 数据库中保存的请求消息结构。
        "response": log.response,  # 数据库中保存的模型回复。
        "prompt_tokens": log.prompt_tokens,
        "completion_tokens": log.completion_tokens,
        "total_tokens": log.total_tokens,
        "latency_ms": log.latency_ms,  # 单次调用耗时，单位为毫秒。
    }


@router.get("/stats")
async def get_llm_stats(db: AsyncSession = Depends(get_db)):
    """获取 LLM 调用聚合统计

    按 function_name 分组统计：
      - 调用次数 / 总Token / 平均延迟
    """
    query = select(
        LLMCallLog.function_name,
        func.count(LLMCallLog.id).label("call_count"),  # 调用次数；label 为统计结果列命名。
        func.sum(LLMCallLog.total_tokens).label("total_tokens"),  # 已保存的总 Token 数之和。
        func.avg(LLMCallLog.latency_ms).label("avg_latency_ms"),  # 平均耗时，单位为毫秒。
        func.max(LLMCallLog.latency_ms).label("max_latency_ms"),  # 该功能耗时最长的一次调用。
        func.sum(LLMCallLog.prompt_tokens).label("total_prompt_tokens"),  # 输入 Token 总量。
        func.sum(LLMCallLog.completion_tokens).label("total_completion_tokens"),  # 输出 Token 总量。
    ).group_by(LLMCallLog.function_name)  # 按功能来源分别统计；功能名为空的记录归为一组。

    result = await db.execute(query)
    rows = result.all()

    stats = []
    for row in rows:
        stats.append({
            "function_name": row.function_name,
            "call_count": row.call_count,
            "total_tokens": row.total_tokens or 0,
            "total_prompt_tokens": row.total_prompt_tokens or 0,
            "total_completion_tokens": row.total_completion_tokens or 0,
            "avg_latency_ms": round(row.avg_latency_ms, 2) if row.avg_latency_ms else 0,  # 平均耗时保留 2 位小数。
            "max_latency_ms": row.max_latency_ms or 0,
        })

    # 全局汇总
    total_tokens = sum(s["total_tokens"] for s in stats)  # 汇总所有功能的 Token 数。
    total_calls = sum(s["call_count"] for s in stats)

    return {
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "estimated_cost": round(total_tokens * 0.000002, 4),  # 固定假设每百万 Token 为 2 美元，仅作估算，不代表模型实际账单。
        "by_function": stats,
    }
