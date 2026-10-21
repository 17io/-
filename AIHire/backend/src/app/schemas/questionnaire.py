#   schemas = Pydantic 模型，负责 API 的"进出门安检"：
#   请求进来先按这里的类校验字段（类型不对直接返回 422），响应出去也按它序列化。
#   和 models 的区别：models 描述数据库表长什么样，schemas 描述接口的请求/响应长什么样。
# 本文件：问卷发送/查询接口的进出格式。

"""问卷相关数据结构，保留原项目的简化版定义。"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ===== 单道题目 =====

class QuestionItem(BaseModel):
    """定义一道题目包含的信息"""

    id: str  # 问卷内部的题号，例如 "q1"；与数据库记录 ID 不同，这里要求字符串
    type: str  # 题型标识，例如 text；当前未限制可用的题型名称
    question: str  # 题目正文，例如“解释 Python 中的异步等待”
    options: Optional[List[str]] = None  # 选项列表；不需要选项时可以为空
    language: Optional[str] = None  # 编程题使用的语言，例如 python；可以不提供


# ===== 问卷信息响应 =====

class QuestionnaireResponse(BaseModel):
    """返回问卷信息；与 models 中同名的答卷数据库模型用途不同"""

    id: int  # 问卷实例 ID，对应 questionnaires 表中的主键
    candidate_id: int
    title: str  # 问卷标题，例如“技术能力评估”
    questions: List[QuestionItem] = []  # 题目列表；原项目固定链接模式下可以是空列表
    status: str  # 问卷状态，例如 draft、sent、completed、expired
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None  # 完成问卷的时间，尚未完成时可以为空
    deadline: Optional[datetime] = None  # 问卷截止时间；此字段本身不会自动触发过期处理

    model_config = {"from_attributes": True}
