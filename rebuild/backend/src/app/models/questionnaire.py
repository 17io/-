# ═══════════════════════════════════════════════════════════════
#     问卷两张表：
#   · Questionnaire：发给候选人的问卷实例（题目是 JSON 列，AI 动态生成的）。
#   · QuestionnaireResponse：候选人的作答 + AI 批卷结果（score/passed）。
#   一份问卷对应一条回复记录，通过 questionnaire_id 关联。
# ═══════════════════════════════════════════════════════════════
"""问卷实例与答卷模型；发送、作答校验和评分由后续业务模块实现。"""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text,
)

from app.database import Base


class Questionnaire(Base):
    """发给某位候选人的问卷实例，题目独立保存为发送时的快照。"""

    __tablename__ = "questionnaires"

    # 问卷 ID：唯一标识一条问卷实例。
    id = Column(
        Integer, primary_key=True, autoincrement=True,
    )

    # 所属候选人：一位候选人可以关联多份问卷。
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id"),  # 关联候选人表
        nullable=False,              # 必须指定候选人
        index=True,                  # 便于按候选人查询
    )

    # 来源模板：允许没有模板；删除模板时保留问卷并将引用设为空。
    template_id = Column(
        Integer,
        ForeignKey("questionnaire_templates.id", ondelete="SET NULL"),
        nullable=True,  # 问卷可独立创建，模板删除后也可保留
        index=True,     # 便于查询某份模板生成的问卷
    )

    # 问卷标题：可以从模板复制，也可以由业务代码指定。
    title = Column(
        String(200), default="技术能力评估问卷",
    )

    # 题目快照：创建实例时由业务代码复制模板题目，保留历史内容。
    questions = Column(
        JSON,
        nullable=False,  # 不能为 SQL NULL；外部链接模式可以传入空列表
    )

    # 状态：draft 草稿、sent 已发送、completed 已完成、expired 已过期。
    status = Column(
        String(20), default="draft",
    )

    # 业务操作发生时再填写对应时间，不在创建时默认填入。
    sent_at = Column(DateTime, nullable=True)       # 发送时间
    completed_at = Column(DateTime, nullable=True)  # 完成时间
    deadline = Column(DateTime, nullable=True)      # 截止时间

    # 催填记录：这些字段保存状态，不会自行触发定时通知。
    reminder_count = Column(Integer, default=0)          # 已提醒次数，默认零次
    last_reminder_at = Column(DateTime, nullable=True)   # 最后一次提醒时间

    # 记录创建时间：统一使用 UTC 时间。
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )


class QuestionnaireResponse(Base):
    """候选人提交的答卷；是否允许重复提交由后续业务规则决定。"""

    __tablename__ = "questionnaire_responses"

    # 答卷 ID：唯一标识一份提交记录。
    id = Column(
        Integer, primary_key=True, autoincrement=True,
    )

    # 关联问卷：没有唯一约束，因此数据层允许同一问卷出现多条答卷。
    questionnaire_id = Column(
        Integer,
        ForeignKey("questionnaires.id"),  # 关联问卷实例
        nullable=False,                  # 必须指定问卷
        index=True,                      # 便于查询问卷的提交记录
    )

    # 提交者：业务代码还需核对其与问卷所属候选人是否一致。
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id"),  # 关联候选人
        nullable=False,              # 必须指定候选人
        index=True,                  # 便于查询候选人的答卷
    )

    # 答案与评分：只有字段定义，具体评分算法在后续服务中实现。
    answers = Column(JSON, nullable=True)          # 答案，例如 {"1": "答案内容"}
    score = Column(Float, nullable=True)           # 总分；未评分时可以为空
    score_breakdown = Column(JSON, nullable=True)  # 各题得分明细
    overall_comment = Column(Text, nullable=True)  # 整体评价
    passed = Column(Boolean, nullable=True)        # True 通过，False 未通过，NULL 未判定

    # 提交时间：在候选人实际提交时由业务代码填写。
    submitted_at = Column(DateTime, nullable=True)

    # 答卷记录创建时间。
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
