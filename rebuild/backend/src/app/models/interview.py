# ═══════════════════════════════════════════════════════════════
#    面试表（interviews）——记录一场面试从排期到出结果的全过程。
#   · proposed_slots 存 AI 生成的可选时段（JSON 列），候选人确认后写入 confirmed_start/end。
#   · status 状态机：pending → awaiting_confirm → confirmed → completed/cancelled/no_show。
#   · feedback 用 JSON 存面试官评价，是"评分优化"模块的训练数据来源。
# ═══════════════════════════════════════════════════════════════
"""面试排期模型"""

from datetime import datetime, UTC
import enum
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from app.database import Base


class InterviewStatus(str, enum.Enum):
    """定义面试安排与执行过程中的状态。"""

    PENDING = "pending"  # 等待安排
    AWAITING_CONFIRM = "awaiting_confirm"  # 等待候选人确认时间
    CONFIRMED = "confirmed"  # 时间已确认
    RESCHEDULING = "rescheduling"  # 正在改期
    COMPLETED = "completed"  # 面试已完成
    CANCELLED = "cancelled"  # 面试已取消
    NO_SHOW = "no_show"  # 候选人未出席


class InterviewRound(str, enum.Enum):
    """定义这场面试属于哪个轮次。"""

    FIRST = "first"  # 初面
    TECHNICAL = "technical"  # 技术面
    HR = "hr"  # HR 面
    FINAL = "final"  # 终面


class Interview(Base):
    """面试ORM模型，对应数据库中的 interviews 表。"""

    # 指定数据库表名。
    __tablename__ = "interviews"

    # 面试 ID：唯一标识一场面试。
    id = Column(
        Integer,  # 整数类型
        primary_key=True,  # 设为主键
        autoincrement=True,  # 新增时由数据库自动生成 ID
    )

    # 所属候选人：一位候选人可以参加多场面试。
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id"),  # 外键，关联候选人表
        nullable=False,  # 必须指定所属候选人
        index=True,  # 便于查询某位候选人的全部面试
    )

    # 面试轮次：默认是初面。
    round = Column(
        String(20),                          # 保存轮次字符串
        default=InterviewRound.FIRST.value,  # 未提供时默认使用 "first"
    )

    # 当前状态：默认等待安排。
    status = Column(
        String(20),                           # 保存状态字符串
        default=InterviewStatus.PENDING.value,  # 未提供时默认使用 "pending"
    )

    # 面试官列表：保存登录用户名，便于后续识别参与面试的账号。
    interviewers = Column(
        JSON,          # JSON 类型，例如 ["hr_zhang", "tech_li"]
        default=list,  # 每条新记录使用独立的空列表
    )

    # 面试时长：以分钟为单位。
    duration_minutes = Column(
        Integer,     # 整数类型，例如 60 分钟
        default=60,  # 未提供时默认使用 60 分钟
    )

    # 可选时段：保存提供给候选人选择的时间段列表。
    proposed_slots = Column(
        JSON,           # JSON 类型，保存多个可选时间段
        nullable=True,  # 尚未生成时段时可以为空
    )

    # 已确认的开始时间：候选人确认后，由业务代码填写。
    confirmed_start = Column(
        DateTime,       # 日期时间类型
        nullable=True,  # 尚未确认时可以为空
    )

    # 已确认的结束时间：候选人确认后，由业务代码填写。
    confirmed_end = Column(
        DateTime,       # 日期时间类型
        nullable=True,  # 尚未确认时可以为空
    )

    # 面试地点：用于保存线下面试地址。
    location = Column(
        String(500),    # 地址最大长度为 500 个字符
        nullable=True,  # 线上面试时可以不填写
    )

    # 会议链接：用于保存线上面试入口。
    meeting_link = Column(
        String(500),    # 链接最大长度为 500 个字符
        nullable=True,  # 线下面试时可以不填写
    )

    # 面试反馈：保存面试官评价、优势、不足和建议结论等信息。
    feedback = Column(
        JSON,           # JSON 类型，用于保存结构化反馈
        nullable=True,  # 尚未提交反馈时可以为空
    )

    # 面试摘要：保存后续分析模块生成的总结文字。
    ai_summary = Column(
        Text,           # 长文本类型
        nullable=True,  # 尚未生成摘要时可以为空
    )

    # 提醒次数：记录已经发送过多少次面试提醒。
    reminder_sent = Column(
        Integer,    # 整数类型，表示次数
        default=0,  # 新建记录时默认尚未发送提醒
    )

    # 创建时间：记录这场面试什么时候被录入系统。
    created_at = Column(
        DateTime,  # 统一按不带时区标记的 UTC 时间存储
        default=lambda: datetime.now(UTC).replace(tzinfo=None),  # 插入时生成
    )

    # 更新时间：记录这条面试数据最近一次修改的时间。
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),   # 新增时生成
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),  # 更新时刷新
    )
