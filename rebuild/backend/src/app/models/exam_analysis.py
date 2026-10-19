# ═══════════════════════════════════════════════════════════════
#   试卷分析表——存外部考试系统（Workmenul）同步来的答卷分析结果。
#   数据来源：定时任务 workmenul_sync.py 拉取，或 exam_analysis.py 的 webhook 推送。
# ═══════════════════════════════════════════════════════════════
"""试卷分析模型 — 存储轻速云回调原始数据 + Dify 分析结果"""

from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float
from app.database import Base


class ExamAnalysis(Base):
    """一条外部答卷对应的考试与分析记录。"""

    __tablename__ = "exam_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 外部考试系统中的答卷编号，用来识别重复同步的数据。
    external_id = Column(String(64), nullable=True, unique=True, comment='外部系统答卷记录ID')

    # 考生信息
    candidate_name = Column(String(100), nullable=False, index=True, comment="考生姓名")
    candidate_phone = Column(String(20), nullable=True, comment="考生手机号")
    candidate_position = Column(String(100), nullable=True, comment="应聘岗位")

    # 考试信息：得分、满分与用时（分钟）；成绩未返回时可以为空。
    exam_title = Column(String(200), nullable=False, comment='考试名称')
    exam_score = Column(Float, nullable=True, comment='考试得分')
    exam_total = Column(Float, nullable=True, comment='满分')
    exam_duration = Column(Integer, nullable=True, comment='用时（分钟）')

    # 原始考试数据与后续分析结果，方便回查和排错。
    raw_data = Column(JSON, nullable=True, comment='外部考试原始数据')
    analysis_result = Column(JSON, nullable=True, comment='分析结果')
    analysis_status = Column(String(20), default='pending', comment='分析状态')
    # 状态由业务代码更新：pending → analyzing → completed / failed。
    error_message = Column(Text, nullable=True, comment='分析失败原因')

    # 创建时生成 UTC 时间；分析完成时间由后续业务代码填写。
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment='创建时间')
    analyzed_at = Column(DateTime, nullable=True, comment='分析完成时间')
