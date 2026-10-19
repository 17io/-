# ═══════════════════════════════════════════════════════════════
#   评分权重迭代表——每次"应用新权重"都记录一版历史（旧权重/新权重/依据）。
#   类似 git 给权重做的版本管理，方便回溯"当时为什么调分"。
# ═══════════════════════════════════════════════════════════════
"""评分权重迭代记录，保存调整前后的权重与操作信息。"""

from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.database import Base


class ScoringIteration(Base):
    """
    每条记录表示一次评分权重调整。

    权重应用本身只写 settings 进程内存（重启回退 .env，与 dashboard /scoring-weights
    一致），但每次应用都会落一张历史表，形成可追溯的迭代记录。
    """

    __tablename__ = "scoring_iterations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 权重适用的岗位类别；空字符串表示默认权重。
    category = Column(String(50), default="", nullable=False)

    # 调整前的权重快照，用来回看原来的评分规则。
    from_weights = Column(JSON, nullable=False)

    # 本次准备应用的新权重。
    to_weights = Column(JSON, nullable=False)

    # 本次调整的原因或说明。
    note = Column(String(500), nullable=True)

    # 操作人的登录用户名，作为本次操作记录保存。
    applied_by = Column(String(50), nullable=True)

    # 本次调整记录的创建时间，统一保存 UTC 时间。
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )