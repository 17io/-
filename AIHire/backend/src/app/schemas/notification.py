#   schemas = Pydantic 模型，负责 API 的"进出门安检"：
#   请求进来先按这里的类校验字段（类型不对直接返回 422），响应出去也按它序列化。
#   和 models 的区别：models 描述数据库表长什么样，schemas 描述接口的请求/响应长什么样。
# 本文件：通知相关接口的进出格式。

"""通知与招聘流程状态的数据结构。"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ===== 发送通知请求 =====

class NotificationRequest(BaseModel):
    """定义发送通知时提交的数据"""

    candidate_id: int
    template: str  # 通知模板名称，例如 questionnaire_invite、interview_invite
    channel: str = "email"  # 发送渠道，默认邮件；业务中还使用 sms、wework、dingtalk


# ===== 通知记录响应 =====

class NotificationResponse(BaseModel):
    """定义返回给前端的通知记录"""

    id: int  # 通知记录 ID，对应 notifications 表中的主键
    type: str  # 已保存的通知渠道；请求中叫 channel，数据库中叫 type
    template: str
    recipient: str  # 最终收件人，例如邮箱地址、手机号码或渠道接收目标
    status: str  # 发送状态，例如 pending、sent、failed
    sent_at: Optional[datetime] = None  # 发送时间，尚未发送时可以为空
    error_message: Optional[str] = None  # 发送失败的原因，正常情况下可以为空

    model_config = {"from_attributes": True}


# ===== 招聘流程状态响应 =====

class WorkflowStatusResponse(BaseModel):
    """原项目保留的流程状态结构，当前状态接口直接返回另一组字典字段"""

    candidate_id: int
    candidate_name: str
    current_stage: str  # 当前所处的招聘阶段，例如简历分析、面试排期
    next_action: str  # 下一步操作标识，例如 schedule_interview
    summary: dict = {}  # 补充信息字典，未提供时默认空字典
