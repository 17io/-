# ═══════════════════════════════════════════════════════════════
#    简历表（resumes）——一位候选人可有多份简历，candidate_id 外键多对一关联。
#   · raw_text：从 PDF/Word 提取的纯文本；analysis_result：JSON 列存 AI 结构化分析结果。
#   · JSON 列的好处：字段结构不固定也能直接存，取出来就是 Python dict。
# ═══════════════════════════════════════════════════════════════
"""简历模型"""
from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from app.database import Base

class Resume(Base):
    """简历ORM模型，对应数据库中的 resumes 表。"""

    __tablename__ = "resumes"

    # 简历 ID：唯一标识每一条简历记录。
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 所属候选人：每份简历必须关联一位候选人。
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False, index=True)

    # 原始文件名：保存用户上传时的文件名称，可以不填写。
    original_filename = Column(String(500), nullable=True)

    # 文件存储路径：记录简历文件保存的位置，可以不填写。
    file_path = Column(String(1000), nullable=True)

    # 文件类型：记录简历格式，例如 pdf、docx、txt。
    file_type = Column(String(10), nullable=True)

    # 简历原始文本：保存文件解析或 OCR 识别后得到的文字。
    raw_text = Column(Text, nullable=True)

    # 结构化分析结果：保存基本信息、技能、教育和工作经历等内容。
    # 默认不提供分析结果
    analysis_result = Column(JSON, nullable=True, default=None)

    # 岗位匹配分析：保存综合评分、维度评分、优势和风险等信息。
    match_analysis = Column(JSON, nullable=True, default=None)

    # 简短总结：保存 AI 生成的候选人概述，便于快速浏览。
    summary = Column(Text, nullable=True)

    # 分析完成时间：由分析服务在处理完成后填写。
    analyzed_at = Column(DateTime, nullable=True)

    # 创建时间：记录这份简历什么时候被录入系统。
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
