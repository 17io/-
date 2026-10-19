# ═══════════════════════════════════════════════════════════════
#   岗位 JD 库表——HR 传简历时不再每次手填招聘标准：
#   这份文档里按「应聘岗位」存了对应的标准岗位说明书（职责+要求），
#   简历分析前自动按候选人的应聘岗位匹配到一份 JD 喂给大模型。
#   页面管理方式与「邮件模板」一致：DB 存储 + 内置默认（可恢复/停用）。
#   · 每个岗位一条生效记录（position 唯一）；停用 = 不再参与自动套用。
#   · 匹配时拿 candidate.position 对 position/aliases 做最长命中，优先手填 JD。
# ═══════════════════════════════════════════════════════════════
"""可配置岗位 JD 模型 — 简历分析自动套用的"招聘标准"库（DB 存储、内置默认兜底）
保存可配置的岗位职责和任职要求。
字段说明：
  - position: 岗位名（如 采购主管/电商运营经理），唯一约束；也是匹配主键。
  - aliases:  匹配别名，顿号分隔（如「城市经理，安徽城市经理」），HR 填的应聘岗位
              只要命中任一名即套用该 JD。
  - category: 分类（采购供应链/销售/市场/运营/研发/职能），用于界面分组。
  - responsibilities/requirements: 岗位职责/任职要求正文（喂给大模型的 JD 文本来源）。
  - salary:    薪资说明（如 面议），仅展示，不进分析提示词。
  - is_system: 是否内置播种（界面标记「系统」，可编辑可删除）。
  - is_active: 停用后该岗位自动套用不再命中。
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from app.database import Base


class PositionJd(Base):
    """一条记录对应一个岗位的招聘标准。"""

    __tablename__ = "position_jds"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 标准岗位名称；同名岗位不能重复保存。
    position = Column(String(100), unique=True, index=True, nullable=False)

    # 岗位别名，保存为字符串，由后续服务拆分并匹配。
    aliases = Column(String(255), nullable=False, default="")

    # 分类名称，供岗位管理时分组。
    category = Column(String(40), nullable=False, default="other")

    # 岗位职责：入职后主要负责哪些工作。
    responsibilities = Column(Text, nullable=False, default="")

    # 任职要求：需要具备哪些技能、经验和条件。
    requirements = Column(Text, nullable=False, default="")

    # 薪资说明，供岗位信息展示。
    salary = Column(String(50), nullable=False, default="")

    # 标记这条岗位标准是否来自系统内置数据。
    is_system = Column(Boolean, nullable=False, default=False)

    # 是否参与后续自动匹配，新建时默认启用。
    is_active = Column(Boolean, nullable=False, default=True)

    # 创建者账号；系统初始化的数据可以不指定创建者。
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 创建时由数据库生成时间，更新时由 SQLAlchemy 加入更新时间表达式。
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        """将岗位标准转换为接口可返回的字典。"""

        return {
            "id": self.id,
            "position": self.position,
            "aliases": self.aliases,
            "category": self.category,
            "responsibilities": self.responsibilities,
            "requirements": self.requirements,
            "salary": self.salary,
            "is_system": bool(self.is_system),
            "is_active": bool(self.is_active),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }