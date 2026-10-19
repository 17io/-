# ═══════════════════════════════════════════════════════════════
#    候选人表（candidates）——全系统最核心的一张表，一行 = 一位应聘者。
#   · 简历表、面试表、问卷表都通过 candidate_id 外键挂在这张表上。
#   · status 是"生命线"：new → analyzed → q_sent/q_done → scheduled/interviewed
#     → hired/rejected，工作流每个节点推进时都会更新它，招聘管道页按它展示进度。
#   · owner_user_id 用于数据权限：普通 HR 只能看分给自己的候选人（见 dependencies/scope.py）。
# ═══════════════════════════════════════════════════════════════
"""候选人模型"""
from datetime import datetime, UTC  # 获取 UTC 时间，用于创建和更新时间
import enum  # 定义候选人的固定状态

from sqlalchemy import (
    Column,      # 定义数据库表中的列
    Integer,     # 整数类型，例如候选人 ID
    String,      # 有长度限制的字符串，例如姓名
    DateTime,    # 日期时间类型
    Float,       # 浮点数类型，例如工作年限、匹配评分
    Text,        # 长文本类型，例如备注
    JSON,        # JSON 类型，例如保存标签列表
    ForeignKey,  # 定义外键，关联其他表中的记录
)

from app.database import Base  # 所有数据模型共同继承的父类

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

    # 指定数据库表名。
    __tablename__ = "candidates"

    # 候选人 ID：唯一标识每位候选人。
    id = Column(
        Integer,             # 整数类型
        primary_key=True,    # 设为主键，唯一标识一条记录
        autoincrement=True,  # 新增记录时，由数据库自动生成递增 ID
    )

    # 候选人姓名：必填，并建立索引，便于按姓名查找。
    name = Column(
        String(100),     # 保存字符串，最大长度设为 100 个字符
        nullable=False,  # 不允许保存为数据库中的 NULL
        index=True,      # 建立索引，便于按姓名查询
    )

    # 联系电话：可以不填写，使用字符串保存。
    phone = Column(
        String(20),     # 保存字符串，最大长度设为 20 个字符
        nullable=True,  # 允许保存为数据库中的 NULL，表示未提供电话
    )

    # 联系邮箱：可以不填写，并建立索引，便于按邮箱查找。
    email = Column(
        String(200),    # 保存字符串，最大长度设为 200 个字符
        nullable=True,  # 允许保存为数据库中的 NULL，表示未提供邮箱
        index=True,     # 建立索引，便于按邮箱查询
    )

    # 候选人来源：记录录入渠道，默认是手动录入。
    source = Column(
        String(50),        # 保存渠道名称，最大长度设为 50 个字符
        default="manual",  # 通过 SQLAlchemy 新增时，未提供来源则使用 manual
    )

    # 来源链接：保存外部平台的候选人页面地址，可以不填写。
    source_url = Column(
        Text,           # 长文本类型，用于保存可能较长的链接
        nullable=True,  # 允许保存为数据库中的 NULL，表示未提供链接
    )

    # 外部平台 ID：保存候选人在来源平台上的记录编号，可以不填写。
    external_id = Column(
        String(200),    # 使用字符串，兼容数字、字母等形式的平台编号
        nullable=True,  # 允许保存为数据库中的 NULL，表示未提供外部编号
    )

    # 应聘岗位：必填，并建立索引，便于按岗位查找候选人。
    position = Column(
        String(200),     # 保存岗位名称，最大长度设为 200 个字符
        nullable=False,  # 不允许保存为数据库中的 NULL
        index=True,      # 建立索引，便于按岗位查询
    )

    # 工作年限：以年为单位，可以保存小数，也可以不填写。
    experience_years = Column(
        Float,          # 浮点数类型，例如 3.5 表示三年半
        nullable=True,  # 允许保存为数据库中的 NULL，表示工作年限未知
    )

    # 岗位分类：保存分类结果，便于筛选和选择对应的评分规则。
    job_category = Column(
        String(50),     # 保存分类名称，例如 python、java、erp
        nullable=True,  # 允许保存为数据库中的 NULL，表示尚未分类
        index=True,     # 建立索引，便于按岗位类别查询
    )

    # 当前状态：新增候选人时默认为 new，后续由业务流程更新。
    status = Column(
        String(20),                         # 保存状态字符串，例如 new、analyzed
        default=CandidateStatus.NEW.value,  # 新增时未提供状态，则默认使用 "new"
        index=True,                         # 建立索引，便于按招聘状态筛选
    )

    # 岗位匹配评分：保存分析后的综合分数，尚未评分时可以为空。
    match_score = Column(
        Float,          # 浮点数类型，支持保存 85.6 这样的分数
        nullable=True,  # 允许保存为数据库中的 NULL，表示尚无评分
    )

    # 人才池记录 ID：保存该候选人关联的人才池记录编号。
    talent_pool_id = Column(
        Integer,        # 整数类型，对应人才池记录的 ID
        nullable=True,  # 允许为空，表示当前没有关联的人才池记录
    )

    # 人才池原因：记录为什么将候选人放入人才池。
    talent_pool_reason = Column(
        String(500),    # 保存原因说明，最大长度设为 500 个字符
        nullable=True,  # 允许为空，表示尚未记录原因
    )

    # 负责人账号 ID：关联用户表，未指派负责人时可以为空。
    owner_user_id = Column(
        Integer,                 # 整数类型，保存负责人账号的 ID
        ForeignKey("users.id"),  # 外键，关联 users 表的 id 列
        nullable=True,           # 允许为空，表示尚未指派负责人
        index=True,              # 建立索引，便于按负责人查询候选人
    )

    # 候选人标签：保存技能等标签，默认是空列表。
    tags = Column(
        JSON,          # JSON 类型，可以保存列表或字典
        default=list,  # 插入记录时未提供标签，则调用 list() 生成新的空列表
    )

    # 创建时间：记录候选人什么时候被录入系统。
    created_at = Column(
        DateTime,  # 日期时间类型，统一按不带时区标记的 UTC 时间存储
        default=lambda: datetime.now(UTC).replace(tzinfo=None),  # 插入时生成当前时间
    )

    # 更新时间：新增时生成，后续修改候选人记录时刷新。
    updated_at = Column(
        DateTime,  # 日期时间类型，统一按不带时区标记的 UTC 时间存储
        default=lambda: datetime.now(UTC).replace(tzinfo=None),   # 新增记录时生成
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),  # 更新记录时刷新
    )









