#   schemas = Pydantic 模型，负责 API 的"进出门安检"：
#   请求进来先按这里的类校验字段（类型不对直接返回 422），响应出去也按它序列化。
#   和 models 的区别：models 描述数据库表长什么样，schemas 描述接口的请求/响应长什么样。
# 本文件：候选人创建/更新/查询的请求与响应格式。

"""候选人与人才池相关Pydantic Schema（数据校验与序列化）"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ===== 创建候选人请求 =====

class CandidateCreate(BaseModel):
    """创建候选人时提交的数据"""

    name: str  # 候选人姓名，必填
    phone: Optional[str] = None  # 联系电话，可以不提供
    email: Optional[str] = None
    position: str  # 应聘岗位名称，必填，例如 Python 开发工程师
    source: str = "manual"  # 来源渠道，默认手动录入；也可记录 boss、linkedin、referral 等
    source_url: Optional[str] = None  # 候选人在外部平台的来源链接
    experience_years: Optional[float] = None  # 工作年限，允许小数，例如 3.5 年
    tags: List[str] = []  # 字符串列表，例如 ["Python", "MySQL"]；默认没有标签
    owner_user_id: Optional[int] = None  # 负责人用户 ID；是否允许指定负责人，由接口检查


# ===== 改派候选人负责人请求 =====

class CandidateOwnerUpdate(BaseModel):
    """重新指定候选人的负责人"""

    owner_user_id: int  # 必须提交新负责人 ID；用户是否存在、角色是否合适，由接口检查


# ===== 更新候选人请求 =====

class CandidateUpdate(BaseModel):
    """修改候选人信息，所有字段都可以不提供"""

    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    position: Optional[str] = None
    status: Optional[str] = None  # 招聘流程中的状态，例如 new、analyzed
    match_score: Optional[float] = None  # 岗位匹配评分；当前数据结构没有设置分数上下限
    tags: Optional[List[str]] = None  # 可不提交；提交 [] 表示希望清空标签
    experience_years: Optional[float] = None
    job_category: Optional[str] = None  # 岗位分类标识，例如 python、java


# ===== 单个候选人响应 =====

class CandidateResponse(BaseModel):
    """返回给前端的候选人信息"""

    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    source: str
    position: str
    experience_years: Optional[float] = None
    job_category: Optional[str] = None
    status: str
    match_score: Optional[float] = None
    tags: List[str] = []
    talent_pool_id: Optional[int] = None  # 对应的人才池记录 ID；没有入池时可以为空
    talent_pool_reason: Optional[str] = None  # 进入人才池的原因
    owner_user_id: Optional[int] = None
    created_at: datetime  # 记录创建时间，从已有记录读取，这里不会自动生成
    updated_at: datetime  # 记录最后更新时间

    model_config = {"from_attributes": True}  # 允许从 ORM 对象属性读取数据


# ===== 候选人分页列表响应 =====

class CandidateListResponse(BaseModel):
    """候选人列表及分页信息"""

    total: int  # 符合查询条件的总记录数
    items: List[CandidateResponse]  # 当前这一页的候选人数据
    page: int  # 当前页码，例如第 1 页
    page_size: int  # 每页最多返回多少条记录


# ===== 单个人才池记录响应 =====

class TalentPoolResponse(BaseModel):
    """返回给前端的人才池记录"""

    id: int
    candidate_id: int  # 这条人才池记录对应的候选人 ID
    original_position: str  # 候选人入池前应聘的岗位
    match_score: Optional[float] = None
    strengths: List[str] = []  # 候选人的优势，例如技术经验、项目经历
    risks: List[str] = []  # 候选人的风险或不足
    pool_reason: Optional[str] = None  # 本条人才池记录保存的入池原因
    suitable_positions: List[str] = []  # 后续可以考虑的岗位列表
    skills: List[str] = []  # 技能列表
    status: str  # 人才池状态，例如 active、contacted、reactivated、archived
    reactivated_at: Optional[datetime] = None  # 从人才池重新激活的时间
    reactivated_for: Optional[str] = None  # 重新激活后应聘的岗位
    contacted_at: Optional[datetime] = None  # 联系候选人的时间
    contact_note: Optional[str] = None  # 联系备注，例如候选人的求职意向
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===== 人才池分页列表响应 =====

class TalentPoolListResponse(BaseModel):
    """人才池列表及分页信息"""

    total: int
    items: List[TalentPoolResponse]
    page: int
    page_size: int


# ===== 从人才池重新激活请求 =====

class ReactivateRequest(BaseModel):
    """选择一条人才池记录，重新应聘指定岗位"""

    talent_pool_id: int  # 要重新激活的人才池记录 ID
    position: str  # 本次重新应聘的岗位


# ===== 加入人才池请求 =====

class TalentPoolCreateRequest(BaseModel):
    """加入人才池时提交的数据"""

    candidate_id: int
    position: str
    match_score: Optional[float] = None