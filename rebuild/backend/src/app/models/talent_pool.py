# ═══════════════════════════════════════════════════════════════
#   人才池表——"现在不合适，但值得保持联系"的候选人存放处。
#   工作流里 40~60 分的候选人会被 move_to_talent_pool 节点写进这张表；
#   HR 之后可以重新激活（reactivate_from_pool，见 routers/workflow.py）。
# ═══════════════════════════════════════════════════════════════
"""人才池模型"""

from datetime import datetime, UTC
import enum
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, JSON
from app.database import Base

class TalentPoolStatus(str, enum.Enum):
    """定义候选人在人才池中的跟进状态。"""

    ACTIVE = "active"            # 在人才池中，等待合适机会
    REACTIVATED = "reactivated"  # 已重新激活，进入新的招聘流程
    CONTACTED = "contacted"      # 已联系候选人
    ARCHIVED = "archived"        # 已归档

class TalentPool(Base):
    """人才池ORM模型，对应数据库中的 talent_pool 表。"""

    __tablename__ = "talent_pool"

    # 人才池记录 ID：唯一标识一条人才池记录。
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 候选人 ID：每位候选人最多对应一条人才池记录。
    # 保存候选人编号
    candidate_id = Column(Integer, nullable=False, unique=True, index=True)

    # 原应聘岗位：记录候选人入池前应聘的岗位。
    original_position = Column(String(200), nullable=False)

    # 匹配分数：保存入池时记录的岗位匹配评分。
    # 浮点数类型，例如 55.6
    match_score = Column(Float, nullable=True)

    # 候选人优势：保存分析得到的优势列表。
    # JSON 类型，例如 ["熟悉 Python", "有接口开发经验"]
    strengths = Column(JSON, default=list)

    # 候选人风险或不足：保存需要关注的问题。
    # JSON 类型，例如 ["相关项目经验较少"]
    risks = Column(JSON, default=list)

    # 入池原因：说明为什么暂时保留候选人。
    pool_reason = Column(String(500), nullable=True)

    # 适合的未来岗位：保存后续可以考虑的岗位列表。
    # JSON 类型，例如 ["Python 开发工程师", "后端开发工程师"]
    suitable_positions = Column(JSON, default=list)

    # 技能标签：保存候选人具备的技能。
    # JSON 类型，例如 ["Python", "FastAPI", "MySQL"]
    skills = Column(JSON, default=list)

    # 人才池状态：新记录默认处于等待机会的状态。
    # 保存状态字符串
    # 默认使用 "active"
    status = Column(String(20), default=TalentPoolStatus.ACTIVE.value, index=True)

    # 重新激活时间：候选人重新进入招聘流程时，由业务代码填写。
    reactivated_at = Column(DateTime, nullable=True)

    # 重新激活后的应聘岗位。
    reactivated_for = Column(String(200), nullable=True)

    # 联系时间：记录业务代码填写的联系时间。
    contacted_at = Column(DateTime, nullable=True)

    # 联系备注：记录联系结果、意向或后续安排。
    contact_note = Column(Text, nullable=True)

    # 创建时间：记录这条人才池记录什么时候建立。
    # 统一按不带时区标记的 UTC 时间存储
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    # 更新时间：记录最近一次修改的时间。
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))
