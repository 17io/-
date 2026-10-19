# ═══════════════════════════════════════════════════════════════
#    用户表（系统登录账号）。
#   · role 区分 admin / hr：admin 看全量数据，hr 只看分给自己的候选人（见 dependencies/scope.py）。
#   · 密码存的是 bcrypt 哈希（dependencies/auth.py 负责加密和校验），绝不存明文。
# ═══════════════════════════════════════════════════════════════
"""用户与角色模型 — JWT 认证 + RBAC 权限管理"""
from datetime import datetime, UTC  # 日期时间工具，以及 UTC 时区
import enum  # 定义固定选项，例如管理员、HR 等角色

# Column：定义数据库中的列；Integer：整数类型，例如用户 ID。
# String：有长度限制的字符串，例如用户名；DateTime：日期时间类型。
# Boolean：布尔类型，保存 True 或 False，例如账号是否启用。
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database import Base  # 所有数据模型共同继承的父类


class UserRole(str, enum.Enum):
    """定义系统中的用户角色。"""

    ADMIN = "admin"  # 管理员
    HR = "hr"  # 招聘人员
    INTERVIEWER = "interviewer"  # 面试官
    CANDIDATE = "candidate"  # 候选人


class User(Base):
    """用户ORM模型，对应数据库中的 users 表。"""

    # 指定数据库表名。
    __tablename__ = "users"

    # 用户 ID，由数据库自动生成。
    # primary_key 将它设为主键，用于唯一标识每个用户
    # autoincrement 新增用户时，由数据库自动生成递增的 ID
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 登录用户名：必填、不能重复，并建立索引。
    username = Column(
        String(100),
        unique=True,  # 用户名不能重复
        nullable=False,  # 不允许保存为数据库中的 NULL
        index=True,  # 建立索引，便于按用户名查找账号
    )

    # 密码哈希：保存密码经过哈希处理后的结果。
    hashed_password = Column(
        String(255),     # 保存字符串，最大长度设为 255 个字符
        nullable=False,  # 不允许保存为数据库中的 NULL
    )

    # 用户角色：未指定时，默认设置为 HR。
    role = Column(
        String(20),                 # 保存角色字符串，最大长度设为 20 个字符
        default=UserRole.HR.value,   # 默认值为前面定义的 "hr"
        nullable=False,             # 不允许保存为数据库中的 NULL
    )

    # 用户邮箱：用于保存账号关联的邮箱地址，可以不填写。
    email = Column(
        String(200),    # 保存字符串，最大长度设为 200 个字符
        nullable=True,  # 允许保存为数据库中的 NULL，表示未提供邮箱
    )

    # 显示姓名：用于界面展示，可以不填写。
    display_name = Column(
        String(100),    # 保存字符串，最大长度设为 100 个字符
        nullable=True,  # 允许保存为数据库中的 NULL，表示未提供显示姓名
    )

    # 账号启用状态：新建账号时默认启用。
    is_active = Column(
        Boolean,       # 布尔类型，保存 True 或 False
        default=True,  # 通过 SQLAlchemy 新增账号时，未提供该字段则默认启用
    )

    # 创建时间：新增用户记录时，默认记录当前 UTC 时间。
    created_at = Column(
        DateTime,                 # 日期时间类型
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        # 插入时才计算时间；保留 UTC 时间数值，去掉时区标记
    )

    # 更新时间：新增记录时生成，后续修改记录时刷新。
    updated_at = Column(
        DateTime,  # 日期时间类型，统一按不带时区标记的 UTC 时间存储
        default=lambda: datetime.now(UTC).replace(tzinfo=None),   # 新增时生成时间
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),  # 更新时重新生成时间
    )