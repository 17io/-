# ═══════════════════════════════════════════════════════════════
#   可配置邮件模板表——原来 7 套邮件模板硬编码在
#   services/notification.py 里，现在迁进数据库，HR/Admin 可在界面上
#   直接改文案、停用，或让 AI 生成草稿后人工微调保存。
#   自动发送时：DB 有生效记录 → 用 DB 文案；没有/停用/删除 → 回退内置默认。
#   7 个内置 code 不变，只是把「存储位置」从代码搬到表里。
# ═══════════════════════════════════════════════════════════════
"""可配置通知模板模型 — 邮件等渠道的 subject/body 模板（DB 优先、内置兜底）

字段说明：
  - code: 场景编码，如 questionnaire_invite / interview_invite / offer / rejection …
          唯一约束；与 NotificationService.TEMPLATES 的 7 个 key 对应。
  - category: 分类（questionnaire / interview / result / other），用于界面分组。
  - subject/body: 模板内容，支持 {占位符}（见 variables 说明）。
  - is_system: 是否内置模板迁移而来（界面标记「系统」徽标，可编辑可删除）。
  - is_active: 停用后该 code 自动发送回退内置默认。
"""

# func：构造 SQL 函数表达式，例如使用 func.now() 获取数据库当前时间。
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from app.database import Base

class NotificationTemplate(Base):
    """通知模板ORM模型，保存可配置的主题和正文。"""

    __tablename__ = "notification_templates"

    # 模板 ID：唯一标识一条模板记录。
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 场景编码：通知服务通过这个编码寻找模板。
    # 例如 interview_invite、questionnaire_invite
    code = Column(String(64), unique=True, index=True, nullable=False)

    # 显示名称：供使用者识别模板用途。
    # 例如“面试邀请”
    # 未提供时默认使用空字符串
    name = Column(String(100), nullable=False, default='')

    # 模板分类：便于按业务场景组织模板。
    # 例如 questionnaire、interview、result、other
    # 未指定分类时归入 other
    category = Column(String(40), nullable=False, default='other')

    # 主题模板：可以包含候选人姓名等占位符。
    subject = Column(String(255), nullable=False, default='')

    # 正文模板：保存通知文案及需要替换的占位符。
    body = Column(Text, nullable=False, default='')

    # 系统模板标记：记录模板是否来自系统内置内容。
    # True 表示系统模板，False 表示普通模板
    # 默认不是系统模板
    is_system = Column(Boolean, nullable=False, default=False)

    # 启用状态：供通知服务判断是否使用这条数据库模板。
    # True 表示启用，False 表示停用
    is_active = Column(Boolean, nullable=False, default=True)

    # 创建者账号：记录这条模板关联的创建者。
    # 系统初始化的模板可以不指定创建者
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # 创建时间：插入时由数据库生成当前时间。
    # 数据库执行 INSERT 时生成默认时间
    created_at = Column(DateTime, server_default=func.now())

    # 更新时间：新增时生成，SQLAlchemy 更新记录时刷新。
    # SQLAlchemy 更新时加入取当前时间的表达式
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        """将模板记录转换为便于接口返回的字典。"""

        return {
            "id": self.id,                    # 模板 ID
            "code": self.code,                # 场景编码
            "name": self.name,                # 显示名称
            "category": self.category,        # 分类
            "subject": self.subject,          # 主题模板
            "body": self.body,                # 正文模板
            "is_system": bool(self.is_system),  # 转换为布尔值
            "is_active": bool(self.is_active),  # 转换为布尔值
            "created_by": self.created_by,    # 创建者 ID

            # 时间存在时转为 ISO 格式字符串，否则返回 None。
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
