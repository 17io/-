# ═══════════════════════════════════════════════════════════════
#   LLM 调用日志表——"AI 花了多少钱、多长时间、答了什么"的全量台账。
#   写入方：agents/tracing.py 的装饰器；查询方：routers/llm_observability.py。
#   做 AI 应用必备的可观测性基础设施。
# ═══════════════════════════════════════════════════════════════
"""LLM 调用日志模型 — 用于可观测性和成本追踪"""

from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float
from app.database import Base


class LLMCallLog(Base):
    """LLM调用日志ORM模型，记录每次LLM调用的全链路信息

    字段说明：
      - function_name: 调用来源标识，如 "resume_analyze" / "rag_chat" / "questionnaire_gen"
      - model: 使用的模型名称
      - system_prompt: 系统提示词（截断前500字符）
      - messages: 用户消息（JSON）
      - response: 模型回复（截断前2000字符）
      - prompt_tokens / completion_tokens / total_tokens: Token用量
      - latency_ms: 调用延迟（毫秒）
    """

    __tablename__ = "llm_call_logs"

    id = Column(
        Integer,
        primary_key=True,    # 主键，唯一标识这条日志。
        autoincrement=True,  # 新增记录时自动生成编号。
    )

    # 日志记录时间，统一保存不带时区标记的 UTC 时间。
    timestamp = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        index=True,  # 建立索引，便于按时间筛选日志。
    )

    # 会话标识，用于归集同一会话中的多次模型调用。
    session_id = Column(
        String(100),
        nullable=True,  # 部分调用没有会话，因此允许为空。
        index=True,    # 便于按会话查询。
    )

    # 调用来源，例如 resume_analyze 或 rag_chat。
    function_name = Column(
        String(50),
        nullable=True,
        index=True,  # 便于按功能筛选日志。
    )

    # 本次调用使用的模型名称。
    model = Column(
        String(100),
        nullable=True,
    )

    # 系统提示词，写入日志前需要将内容控制在 500 字符内。
    system_prompt = Column(
        String(500),
        nullable=True,
    )

    # 请求消息列表，保存角色、内容等结构化信息。
    messages = Column(
        JSON,
        nullable=True,
    )

    # 模型返回的文本。
    response = Column(
        Text,
        nullable=True,
    )

    # 输入 Token 数量，包括提示词和请求消息等内容。
    prompt_tokens = Column(
        Integer,
        default=0,  # 插入时未提供该字段，则默认保存 0。
    )

    # 输出 Token 数量，即模型生成内容的用量。
    completion_tokens = Column(
        Integer,
        default=0,
    )

    # 本次调用的总 Token 数量。
    total_tokens = Column(
        Integer,
        default=0,
    )

    # 本次模型调用的耗时，单位为毫秒。
    latency_ms = Column(
        Float,
        default=0.0,  # 支持保存带小数的耗时。
    )

    def to_dict(self) -> dict:
        """将日志的主要信息转换为字典，供接口返回。"""

        return {
            "id": self.id,

            # 将日期时间转换为字符串；没有时间时返回空字符串。
            "timestamp": self.timestamp.isoformat() if self.timestamp else "",

            "session_id": self.session_id,
            "function_name": self.function_name,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
        }