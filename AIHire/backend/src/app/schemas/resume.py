#   schemas = Pydantic 模型，负责 API 的"进出门安检"：
#   请求进来先按这里的类校验字段（类型不对直接返回 422），响应出去也按它序列化。
#   和 models 的区别：models 描述数据库表长什么样，schemas 描述接口的请求/响应长什么样。
# 本文件：简历上传/分析结果接口的进出格式。
"""简历接口的数据结构：上传响应、信息提取结果和岗位匹配结果。"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ===== 简历上传成功响应 =====

class ResumeUploadResponse(BaseModel):
    """上传成功后返回的数据"""

    id: int  # 简历记录 ID，对应 resumes 表中的主键
    candidate_id: int
    original_filename: str  # 上传文件的原始名称，例如 张三的简历.pdf
    status: str = "uploaded"  # 默认返回的上传状态
    message: str = "简历上传成功，正在分析中..."  # 默认提示文案；这句话本身不会启动分析


# ===== 简历结构化提取结果 =====

class ResumeAnalysisResult(BaseModel):
    """保存从简历中提取出来的信息"""

    basic_info: dict = {}  # 基本信息字典，例如姓名、电话、邮箱、所在地
    education: List[dict] = []  # 教育经历列表，每个字典代表一段教育经历
    work_experience: List[dict] = []  # 工作经历列表，每个字典代表一段工作经历
    skills: List[str] = []
    projects: List[dict] = []  # 项目经历列表，每个字典代表一个项目
    certifications: List[str] = []  # 证书列表，例如 ["软件设计师", "大学英语六级"]


# ===== 岗位匹配分析结果 =====

class MatchAnalysis(BaseModel):
    """保存候选人与岗位的匹配分析结果"""

    overall_score: float  # 总体匹配评分，业务上按 0～100 使用；此处未设置数值上下限
    dimensions: dict = {}  # 各维度评分，例如 {"skills_match": 90, "experience_match": 80}
    strengths: List[str] = []
    risks: List[str] = []
    recommended_questions: List[str] = []  # 建议面试时进一步询问的问题


# ===== 简历分析结果响应 =====

class ResumeAnalysisResponse(BaseModel):
    """将简历信息、提取结果和匹配结果统一返回给前端"""

    id: int
    candidate_id: int
    candidate_name: str = ""  # 候选人姓名，未提供时默认空字符串
    original_filename: Optional[str] = None
    analysis: Optional[ResumeAnalysisResult] = None  # 嵌套的简历结构化信息，可以暂时没有结果
    match_analysis: Optional[MatchAnalysis] = None  # 嵌套的岗位匹配分析，可以暂时没有结果
    summary: Optional[str] = None  # AI 生成的简短总结
    analyzed_at: Optional[datetime] = None  # 分析完成时间；未分析时可以为空

    model_config = {"from_attributes": True}


# ===== 简历分析请求的数据结构 =====

class ResumeAnalysisRequest(BaseModel):
    """原项目保留的分析请求结构，当前分析接口没有使用这个类作为请求体"""

    candidate_id: int
    job_description: str = ""  # 岗位描述，简称 JD；未提供时默认空字符串