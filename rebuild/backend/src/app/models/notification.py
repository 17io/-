# ═══════════════════════════════════════════════════════════════
# 通知记录表——每次发邮件/短信/机器人消息都留一条底，方便追溯"发没发过"。
# ═══════════════════════════════════════════════════════════════
"""通知记录模型"""
from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from app.database import Base

class Notification(Base):
    """通知记录ORM模型，对应数据库中的 notifications 表。"""

    # 指定数据库表名。
    __tablename__ = "notifications"

    # 通知 ID：唯一标识一条通知记录。
    id = Column(
        Integer,             # 整数类型
        primary_key=True,    # 设为主键
        autoincrement=True,  # 新增时由数据库自动生成 ID
    )

    # 关联候选人：系统类通知可以不关联具体候选人。
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id"),  # 外键，关联候选人表
        nullable=True,               # 允许为空
        index=True,                  # 便于查询某位候选人的通知记录
    )

    # 通知渠道：记录使用邮件、短信或其他消息渠道。
    type = Column(
        String(50),      # 例如 email、sms、wework、dingtalk
        nullable=False,  # 必须指定通知渠道
    )

    # 模板名称：记录本次通知使用的模板标识。
    template = Column(
        String(100),     # 例如 questionnaire_invite、interview_invite
        nullable=False,  # 必须指定模板名称
    )

    # 接收人：根据渠道保存邮箱地址、电话号码等目标信息。
    recipient = Column(
        String(500),     # 接收目标字符串，最大长度为 500 个字符
        nullable=False,  # 必须指定接收目标
    )

    # 通知主题：邮件可以使用主题，其他渠道可以不填写。
    subject = Column(
        String(500),    # 主题最大长度为 500 个字符
        nullable=True,  # 允许为空
    )

    # 通知正文：保存本次通知的具体内容。
    content = Column(
        Text,           # 长文本类型，支持保存较长的正文
        nullable=True,  # 尚未生成正文时可以为空
    )

    # 发送状态：记录通知是等待发送、已发送，还是发送失败。
    status = Column(
        String(20),         # 保存 pending、sent、failed 等状态字符串
        default="pending",  # 新记录默认等待发送
    )

    # 错误信息：发送失败时，保存便于排查的原因。
    error_message = Column(
        Text,           # 长文本类型，用于记录错误说明
        nullable=True,  # 没有错误时可以为空
    )

    # 实际发送时间：由通知服务在发送成功后填写。
    sent_at = Column(
        DateTime,       # 日期时间类型
        nullable=True,  # 尚未成功发送时可以为空
    )

    # 创建时间：记录这条通知数据什么时候建立。
    created_at = Column(
        DateTime,  # 统一按不带时区标记的 UTC 时间存储
        default=lambda: datetime.now(UTC).replace(tzinfo=None),  # 插入时生成
    )