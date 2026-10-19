# ═══════════════════════════════════════════════════════════════
#     问卷模板表：
#   · QuestionnaireTemplate：保存可复用的问卷标题、岗位分类和题目（JSON）。
#   · 创建问卷时复制模板题目，保留独立快照，避免模板修改影响历史问卷。
#   一份模板可关联多份问卷，通过问卷表的 template_id 关联模板表的 id。
# ═══════════════════════════════════════════════════════════════
"""可重复使用的问卷模板；发送实例另行保存题目快照。"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text

from app.database import Base


class QuestionnaireTemplate(Base):
    """问卷模板，对应 questionnaire_templates 表。"""

    __tablename__ = "questionnaire_templates"

    # 模板 ID：唯一标识一份可重复使用的模板。
    id = Column(
        Integer,             # 整数类型
        primary_key=True,    # 设为主键
        autoincrement=True,  # 新增时由数据库自动生成 ID
    )

    # 模板标题：用于识别模板，例如“Python 后端基础评估”。
    title = Column(
        String(200),     # 标题最大长度为 200 个字符
        nullable=False,  # 不允许为数据库中的 NULL
    )

    # 模板说明：记录用途或使用注意事项，可以不填写。
    description = Column(
        Text,           # 长文本类型
        nullable=True,  # 允许为空
    )

    # 适用岗位类别：后续可以按 python、java 等类别选择模板。
    job_category = Column(
        String(50),     # 岗位分类名称，最大长度为 50 个字符
        nullable=True,  # 允许为空，表示没有指定分类
        index=True,     # 建立索引，便于按岗位类别筛选
    )

    # 模板题目：保存题号、题型、题干和选项等结构化内容。
    questions = Column(
        JSON,            # JSON 类型，业务代码应传入题目列表
        nullable=False,  # 不允许为数据库中的 SQL NULL
        default=list,    # 未提供题目时，为新记录生成独立的空列表
    )

    # 启用状态：业务接口后续根据此字段决定模板是否可选。
    is_active = Column(
        Boolean,         # True 表示启用，False 表示停用
        nullable=False,  # 必须有明确的启用状态
        default=True,    # 新模板默认启用
    )

    # 创建时间：统一按不带时区标记的 UTC 时间存储。
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),  # 插入时生成
    )

    # 更新时间：修改模板内容并保存时刷新。
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),   # 新增时生成
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),  # 更新时刷新
    )

    @property
    def question_count(self) -> int:
        """根据当前题目列表计算题数，避免额外计数字段与题目不一致。"""
        return len(self.questions or [])
