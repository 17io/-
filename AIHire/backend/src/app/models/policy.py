# ═══════════════════════════════════════════════════════════════
#    制度文档表——RAG 问答的"原料登记表"。
#   · 上传的制度文档先在这里登记（元数据+状态），再由 rag_service 切块向量化进 Milvus。
#   · status 记录索引进度：uploaded → indexing → indexed / failed。
# ═══════════════════════════════════════════════════════════════
"""企业制度相关模型"""

from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from app.database import Base


class PolicyDocument(Base):
    """企业制度文档ORM模型，对应 policy_documents 表。"""

    __tablename__ = "policy_documents"

    # 文档 ID：唯一标识一份制度文档。
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 文档标题：用于识别文档内容。
    title = Column(String(500), nullable=False)

    # 制度分类：便于组织和筛选文档。
    # 例如员工手册、考勤制度、薪酬福利
    category = Column(String(100), nullable=True)

    # 上传文件名：记录原始文件的名称。
    file_name = Column(String(500), nullable=True)

    # 文档全文：保存解析或人工录入后得到的文字。
    content = Column(Text, nullable=True)

    # 分块数量：由分块或索引服务处理后填写。
    chunk_count = Column(Integer, default=0)

    # 索引完成标记：记录文档是否已完成向量索引。
    # True 表示已标记为完成索引
    indexed = Column(Boolean, default=False)

    # 创建时间：记录制度文档什么时候进入系统。
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    # 更新时间：记录文档数据最近一次修改的时间。
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))


class PolicyChatHistory(Base):
    """制度问答消息ORM模型，对应 policy_chat_history 表。"""

    __tablename__ = "policy_chat_history"

    # 消息 ID：唯一标识一条对话消息。
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 会话 ID：将同一次对话中的多条消息归到一起。
    # 保存会话标识
    session_id = Column(String(100), nullable=False, index=True)

    # 所属账号：记录这条消息属于哪个登录用户。
    # 保存登录用户名
    # 沿用原项目，允许历史记录没有账号信息
    username = Column(String(100), nullable=True, index=True)

    # 消息角色：区分用户提问和 AI 回答。
    # 例如 user、assistant
    role = Column(String(20), nullable=False)

    # 消息正文：保存本条提问或回答。
    content = Column(Text, nullable=False)

    # 检索片段：保存本次回答参考的相关文档块信息。
    retrieved_chunks = Column(JSON, nullable=True)

    # 置信度标签：保存业务代码提供的判断标签。
    # 例如 high、medium、low
    confidence = Column(String(20), nullable=True)

    # 引用来源：保存回答使用的文档来源信息。
    cited_sources = Column(JSON, nullable=True)

    # 消息创建时间：用于记录消息产生时间及查询时排序。
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
