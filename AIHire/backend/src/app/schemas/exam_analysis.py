#   schemas = Pydantic 模型，负责 API 的"进出门安检"：
#   请求进来先按这里的类校验字段（类型不对直接返回 422），响应出去也按它序列化。
#   和 models 的区别：models 描述数据库表长什么样，schemas 描述接口的请求/响应长什么样。
# 本文件：试卷分析数据的进出格式。

"""试卷分析数据结构：记录查询、分页列表和外部答卷导入。"""

from datetime import datetime
from typing import Optional, Any, Literal  # Any 不限定具体结构；Literal 限制为列出的固定值
from pydantic import BaseModel


# ===== 单条试卷分析记录响应 =====

class ExamAnalysisResponse(BaseModel):
    """返回一条考试成绩与分析记录"""

    id: int  # 试卷分析记录 ID，对应 exam_analyses 表中的主键
    candidate_name: str
    candidate_phone: Optional[str] = None  # 考生联系电话
    candidate_position: Optional[str] = None  # 考生应聘的岗位
    external_id: Optional[str] = None  # 外部答卷编号，供服务识别重复导入的记录
    exam_title: str  # 考试或测评名称
    exam_score: Optional[float] = None  # 实际考试得分
    exam_total: Optional[float] = None  # 本场考试的满分，与得分分开保存
    exam_duration: Optional[int] = None  # 考试用时，单位为分钟
    analysis_status: str  # 分析状态，例如 pending、analyzing、completed、failed
    analysis_result: Optional[Any] = None  # 分析结果，保留原代码的灵活数据结构
    raw_data: Optional[Any] = None  # 外部系统传来的原始数据，用于回查
    error_message: Optional[str] = None
    created_at: datetime
    analyzed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ===== 试卷分析分页列表响应 =====

class ExamAnalysisListResponse(BaseModel):
    """返回分析记录列表和分页信息"""

    total: int
    items: list[ExamAnalysisResponse]  # 内置 list 的类型标注写法，与 List[ExamAnalysisResponse] 作用相同
    page: int
    page_size: int


# ===== 外部答卷导入请求 =====

class ExamImportRequest(BaseModel):
    """接收外部答卷数据；幂等导入由后续业务服务实现"""

    external_id: str  # 导入时必填，用于后续查询已有记录；这里没有设置非空字符串限制
    candidate_name: str
    exam_title: str
    candidate_phone: Optional[str] = None
    candidate_position: Optional[str] = None
    exam_score: Optional[float] = None
    exam_total: Optional[float] = None
    exam_duration: Optional[int] = None
    analysis_status: Literal["pending", "analyzing", "completed", "failed"] = "completed"  # 仅允许这四个状态
    analysis_result: Optional[Any] = None
    raw_data: Optional[Any] = None
    error_message: Optional[str] = None

    model_config = {"extra": "allow"}  # 保留未在类中声明的额外请求字段


# ===== 外部答卷导入响应 =====

class ExamImportResponse(BaseModel):
    """返回导入后的记录 ID，以及是否新建记录"""

    id: int
    created: bool  # True 表示本次新建，False 表示更新已有记录
