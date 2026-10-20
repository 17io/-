#   schemas = Pydantic 模型，负责 API 的"进出门安检"：
#   请求进来先按这里的类校验字段（类型不对直接返回 422），响应出去也按它序列化。
#   和 models 的区别：models 描述数据库表长什么样，schemas 描述接口的请求/响应长什么样。
#   本文件：面试排期/反馈等接口的进出格式。

"""面试接口的数据结构：时间段生成、排期确认、手动排期和面试反馈。"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ===== 单个面试时间段 =====

class TimeSlot(BaseModel):
    """描述一个可选的面试时间段"""

    date: str  # 日期字符串，例如 "2026-10-22"
    start_time: str  # 开始时间字符串，例如 "10:00"
    end_time: str  # 结束时间字符串，例如 "11:00"


# ===== 生成可选面试时间段请求 =====

class InterviewSlotRequest(BaseModel):
    """提交排期条件，由后面的服务生成可选时间段"""

    candidate_id: int
    interviewers: List[str] = ["面试官"]  # 面试官字符串列表，默认值是占位名称
    duration_minutes: int = 60  # 单场面试时长，单位为分钟
    round: str = "first"  # 面试轮次，默认初面；业务中还使用 technical、hr、final
    date_range_start: str  # 可安排日期范围的起点，必填，例如 "2026-10-22"
    date_range_end: str  # 可安排日期范围的终点，必填，例如 "2026-10-26"
    working_hours_start: str = "09:00"  # 每天允许安排面试的开始时间
    working_hours_end: str = "18:00"  # 每天允许安排面试的结束时间
    exclude_dates: List[str] = []  # 需要排除的日期列表，例如 ["2026-10-23"]


# ===== 可选面试时间段响应 =====

class InterviewSlotResponse(BaseModel):
    """返回面试记录 ID 和推荐的时间段列表"""

    interview_id: int  # 面试记录 ID，对应 interviews 表中的主键
    proposed_slots: List[TimeSlot]  # 可选时间段列表，每一项按 TimeSlot 的结构处理


# ===== 确认面试时间请求 =====

class SlotConfirm(BaseModel):
    """提交选中的时间段，以及面试地点或会议链接"""

    interview_id: int
    selected_slot: TimeSlot  # 本次选中的时间段，包含日期、开始时间和结束时间
    location: Optional[str] = None  # 线下面试地点，可以不提供
    meeting_link: Optional[str] = None  # 线上会议链接，可以不提供


# ===== 手动排期请求 =====

class ManualScheduleRequest(BaseModel):
    """直接提交确定的面试时间"""

    candidate_id: int
    interviewers: List[str] = ["面试官"]
    round: str = "first"
    date: str
    start_time: str
    end_time: str
    location: Optional[str] = None
    meeting_link: Optional[str] = None


# ===== 面试信息响应 =====

class InterviewResponse(BaseModel):
    """返回一场面试的安排及结果"""

    id: int
    candidate_id: int
    candidate_name: str = ""
    round: str
    status: str  # 面试状态，例如 awaiting_confirm、confirmed、completed
    interviewers: List[str] = []
    proposed_slots: Optional[List[TimeSlot]] = None
    confirmed_start: Optional[datetime] = None  # 最终确认的开始日期与时间
    confirmed_end: Optional[datetime] = None  # 最终确认的结束日期与时间
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    feedback: Optional[dict] = None  # 已保存的面试反馈，按字典返回
    ai_summary: Optional[str] = None  # AI 生成的面试摘要，可以暂时没有

    model_config = {"from_attributes": True}


# ===== 提交面试反馈请求 =====

class InterviewFeedback(BaseModel):
    """面试官提交的评价和建议"""

    interview_id: int
    interviewer: str  # 提交反馈的面试官
    rating: int  # 面试评分，业务约定为 1～5 分；此处没有设置数值上下限
    strengths: List[str] = []
    weaknesses: List[str] = []  # 面试中发现的不足
    decision: str  # 面试建议：pass 通过、reject 拒绝、pending 待定
    detail: str = ""  # 详细评价，未提供时默认空字符串