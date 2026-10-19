# ═══════════════════════════════════════════════════════════════
# 通知记录表——每次发邮件/短信/机器人消息都留一条底，方便追溯"发没发过"。
# ═══════════════════════════════════════════════════════════════
"""通知记录模型"""
from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from app.database import Base

class Notification(Base):
    """通知记录ORM模型，对应数据库中的 notifications 表。"""

    __tablename__ = "notifications"

    # 通知 ID：唯一标识一条通知记录。
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联候选人：系统类通知可以不关联具体候选人。
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=True, index=True)

    # 通知渠道：记录使用邮件、短信或其他消息渠道。
    # 例如 email、sms、wework、dingtalk
    type = Column(String(50), nullable=False)

    # 模板名称：记录本次通知使用的模板标识。
    # 例如 questionnaire_invite、interview_invite
    template = Column(String(100), nullable=False)

    # 接收人：根据渠道保存邮箱地址、电话号码等目标信息。
    recipient = Column(String(500), nullable=False)

    # 通知主题：邮件可以使用主题，其他渠道可以不填写。
    subject = Column(String(500), nullable=True)

    # 通知正文：保存本次通知的具体内容。
    content = Column(Text, nullable=True)

    # 发送状态：记录通知是等待发送、已发送，还是发送失败。
    # 保存 pending、sent、failed 等状态字符串
    # 新记录默认等待发送
    status = Column(String(20), default='pending')

    # 错误信息：发送失败时，保存便于排查的原因。
    error_message = Column(Text, nullable=True)

    # 实际发送时间：由通知服务在发送成功后填写。
    sent_at = Column(DateTime, nullable=True)

    # 创建时间：记录这条通知数据什么时候建立。
    # 统一按不带时区标记的 UTC 时间存储
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
