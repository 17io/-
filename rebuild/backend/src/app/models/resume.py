# ═══════════════════════════════════════════════════════════════
#    简历表（resumes）——一位候选人可有多份简历，candidate_id 外键多对一关联。
#   · raw_text：从 PDF/Word 提取的纯文本；analysis_result：JSON 列存 AI 结构化分析结果。
#   · JSON 列的好处：字段结构不固定也能直接存，取出来就是 Python dict。
# ═══════════════════════════════════════════════════════════════
"""简历模型"""
from datetime import datetime, UTC  # 获取 UTC 时间，用于记录创建时间

from sqlalchemy import (
    Column,      # 定义数据库表中的列
    Integer,     # 整数类型，例如简历 ID、候选人 ID
    String,      # 有长度限制的字符串，例如文件名
    DateTime,    # 日期时间类型，例如分析完成时间
    Text,        # 长文本类型，用于保存简历原文
    JSON,        # JSON 类型，用于保存结构化分析结果
    ForeignKey,  # 定义外键，将简历关联到候选人
)

from app.database import Base  # 数据模型共同继承的父类

class Resume(Base):
    """简历ORM模型，对应数据库中的 resumes 表。"""

    # 指定数据库表名。
    __tablename__ = "resumes"

    # 简历 ID：唯一标识每一条简历记录。
    id = Column(
        Integer,             # 整数类型
        primary_key=True,    # 设为主键，唯一标识一条记录
        autoincrement=True,  # 新增记录时，由数据库自动生成递增 ID
    )

    # 所属候选人：每份简历必须关联一位候选人。
    candidate_id = Column(
        Integer,                      # 整数类型，保存候选人 ID
        ForeignKey("candidates.id"),  # 外键，关联 candidates 表的 id 列
        nullable=False,              # 不允许为 NULL，必须指定所属候选人
        index=True,                  # 建立索引，便于查询某位候选人的全部简历
    )

    # 原始文件名：保存用户上传时的文件名称，可以不填写。
    original_filename = Column(
        String(500),    # 保存字符串，最大长度设为 500 个字符
        nullable=True,  # 允许为空，例如直接录入简历文本时没有上传文件
    )

    # 文件存储路径：记录简历文件保存的位置，可以不填写。
    file_path = Column(
        String(1000),   # 保存路径字符串，最大长度设为 1000 个字符
        nullable=True,  # 允许为空，例如直接录入简历文本时没有文件路径
    )

    # 文件类型：记录简历格式，例如 pdf、docx、txt。
    file_type = Column(
        String(10),     # 保存类型字符串，最大长度设为 10 个字符
        nullable=True,  # 允许为空，例如直接录入简历文本时没有文件类型
    )

    # 简历原始文本：保存文件解析或 OCR 识别后得到的文字。
    raw_text = Column(
        Text,           # 长文本类型，用于保存整份简历的文字内容
        nullable=True,  # 允许为空，表示尚未提取到文本
    )

    # 结构化分析结果：保存基本信息、技能、教育和工作经历等内容。
    analysis_result = Column(
        JSON,           # JSON 类型，可以保存字典、列表等结构化数据
        nullable=True,  # 允许数据库列为 NULL，尚未分析时可以暂不填写
        default=None,   # 默认不提供分析结果
    )

    # 岗位匹配分析：保存综合评分、维度评分、优势和风险等信息。
    match_analysis = Column(
        JSON,           # JSON 类型，用于保存结构化的匹配分析结果
        nullable=True,  # 允许为空，表示尚未获得匹配分析结果
        default=None,   # 默认不提供匹配分析结果
    )

    # 简短总结：保存 AI 生成的候选人概述，便于快速浏览。
    summary = Column(
        Text,           # 长文本类型，用于保存总结文字
        nullable=True,  # 允许为空，表示尚未生成总结
    )

    # 分析完成时间：由分析服务在处理完成后填写。
    analyzed_at = Column(
        DateTime,       # 日期时间类型，按统一的 UTC 时间约定写入
        nullable=True,  # 允许为空，表示尚未记录分析完成时间
    )

    # 创建时间：记录这份简历什么时候被录入系统。
    created_at = Column(
        DateTime,  # 日期时间类型，统一按不带时区标记的 UTC 时间存储
        default=lambda: datetime.now(UTC).replace(tzinfo=None),  # 插入时生成时间
    )





