#   schemas = Pydantic 模型，负责 API 的"进出门安检"：
#   请求进来先按这里的类校验字段（类型不对直接返回 422），响应出去也按它序列化。
#   和 models 的区别：models 描述数据库表长什么样，schemas 描述接口的请求/响应长什么样。
# 本文件：注册/登录/改密码等接口的请求体定义。
"""认证接口的数据结构：定义请求字段、校验规则和响应字段。"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models import UserRole


# ===== 登录请求 =====

class LoginRequest(BaseModel):
    """登录请求"""

    # Field 中的 ... 表示必填；min_length、max_length 限制长度；description 是字段说明。
    username: str = Field(..., min_length=2, max_length=100, description="用户名")
    password: str = Field(..., min_length=4, max_length=128, description="密码")


# ===== 登录成功响应 =====

class TokenResponse(BaseModel):
    """登录成功后返回的数据"""

    access_token: str  # 登录令牌，由后面的认证逻辑生成
    token_type: str = "bearer"  # 令牌类型；前端通常通过 Authorization: Bearer <令牌> 携带
    username: str
    role: str  # 用户角色，例如 admin、hr、interviewer


# ===== 创建用户请求 =====

class UserCreate(BaseModel):
    """创建账号时提交的数据，操作权限由接口检查"""

    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=4, max_length=128)
    role: UserRole = UserRole.HR  # 使用角色枚举校验，未提供时默认是 HR
    email: Optional[str] = None  # 联系邮箱，可以不提供；当前只检查字符串类型，不检查邮箱格式
    display_name: Optional[str] = None  # 界面展示的姓名，可以不提供


# ===== 首个管理员初始化请求 =====

class SetupAdminRequest(BaseModel):
    """系统初始化时，创建首个管理员需要提交的数据"""

    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=128, description="管理员密码（至少6位）")
    email: Optional[str] = None


# ===== 更新当前用户资料请求 =====

class UpdateProfileRequest(BaseModel):
    """修改当前用户的显示姓名"""

    display_name: Optional[str] = Field(None, max_length=100, description="显示姓名")  # 可不提供；清除姓名的逻辑由接口处理


# ===== 修改密码请求 =====

class ChangePasswordRequest(BaseModel):
    """修改密码时提交的旧密码和新密码"""

    old_password: str = Field(..., min_length=4, max_length=128)  # 旧密码，后续用于验证操作者是否知道当前密码
    new_password: str = Field(..., min_length=4, max_length=128)  # 新密码，后续经过哈希处理再保存


# ===== 用户信息响应 =====

class UserResponse(BaseModel):
    """返回给前端的用户信息，不包含密码和密码哈希"""

    id: int  # 数据库中的用户唯一编号
    username: str
    role: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    is_active: bool  # 账号是否启用，True 表示启用，False 表示禁用

    model_config = ConfigDict(from_attributes=True)  # 允许从 ORM 对象的属性读取数据