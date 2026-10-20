# ═══════════════════════════════════════════════════════════════
#    候选人表（candidates）——全系统最核心的一张表，一行 = 一位应聘者。
#   · 简历表、面试表、问卷表都通过 candidate_id 外键挂在这张表上。
#   · status 是"生命线"：new → analyzed → q_sent/q_done → scheduled/interviewed
#     → hired/rejected，工作流每个节点推进时都会更新它，招聘管道页按它展示进度。
#   · owner_user_id 用于数据权限：普通 HR 只能看分给自己的候选人（见 dependencies/scope.py）。
# ═══════════════════════════════════════════════════════════════
"""候选人模型"""
from datetime import datetime, UTC
import enum

# Float：浮点数类型，例如工作年限、匹配评分；Text：长文本类型，例如备注。
# JSON：JSON 类型，例如保存标签列表；ForeignKey：定义外键，关联其他表中的记录。
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, JSON, ForeignKey
from app.database import Base

class CandidateStatus(str, enum.Enum):
    """定义候选人在招聘流程中的状态。"""

    NEW = "new"                  # 新录入，尚未处理
    RESUME_ANALYZED = "analyzed"  # 简历已完成分析
    TALENT_POOL = "talent_pool"   # 已进入人才池，留待后续岗位匹配

    QUESTIONNAIRE_SENT = "q_sent"  # 问卷已发送，等待候选人填写
    QUESTIONNAIRE_DONE = "q_done"  # 问卷已完成，等待后续处理

    INTERVIEW_SCHEDULED = "scheduled"  # 已确认面试时间，等待面试
    INTERVIEWED = "interviewed"        # 已完成面试，等待评审或后续处理

    REJECTED = "rejected"  # 已拒绝，本次招聘流程不再继续
    HIRED = "hired"        # 已录用
    ARCHIVED = "archived"  # 已归档，保留候选人记录供后续查询

class Candidate(Base):
    """候选人ORM模型，对应数据库中的 candidates 表。"""

    __tablename__ = "candidates"

    # 候选人 ID：唯一标识每位候选人。
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 候选人姓名：必填，并建立索引，便于按姓名查找。
    name = Column(String(100), nullable=False, index=True)

    # 联系电话：可以不填写，使用字符串保存。
    phone = Column(String(20), nullable=True)

    # 联系邮箱：可以不填写，并建立索引，便于按邮箱查找。
    email = Column(String(200), nullable=True, index=True)

    # 候选人来源：记录录入渠道，默认是手动录入。
    # 通过 SQLAlchemy 新增时，未提供来源则使用 manual
    source = Column(String(50), default='manual')

    # 来源链接：保存外部平台的候选人页面地址，可以不填写。
    source_url = Column(Text, nullable=True)

    # 外部平台 ID：保存候选人在来源平台上的记录编号，可以不填写。
    # 使用字符串，兼容数字、字母等形式的平台编号
    external_id = Column(String(200), nullable=True)

    # 应聘岗位：必填，并建立索引，便于按岗位查找候选人。
    position = Column(String(200), nullable=False, index=True)

    # 工作年限：以年为单位，可以保存小数，也可以不填写。
    # 浮点数类型，例如 3.5 表示三年半
    experience_years = Column(Float, nullable=True)

    # 岗位分类：保存分类结果，便于筛选和选择对应的评分规则。
    # 保存分类名称，例如 python、java、erp
    job_category = Column(String(50), nullable=True, index=True)

    # 当前状态：新增候选人时默认为 new，后续由业务流程更新。
    # 保存状态字符串，例如 new、analyzed
    # 新增时未提供状态，则默认使用 "new"
    status = Column(String(20), default=CandidateStatus.NEW.value, index=True)

    # 岗位匹配评分：保存分析后的综合分数，尚未评分时可以为空。
    match_score = Column(Float, nullable=True)

    # 人才池记录 ID：保存该候选人关联的人才池记录编号。
    talent_pool_id = Column(Integer, nullable=True)

    # 人才池原因：记录为什么将候选人放入人才池。
    talent_pool_reason = Column(String(500), nullable=True)

    # 负责人账号 ID：关联用户表，未指派负责人时可以为空。
    owner_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)

    # 候选人标签：保存技能等标签，默认是空列表。
    # 插入记录时未提供标签，则调用 list() 生成新的空列表
    tags = Column(JSON, default=list)

    # 创建时间：记录候选人什么时候被录入系统。
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    # 更新时间：新增时生成，后续修改候选人记录时刷新。
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))
