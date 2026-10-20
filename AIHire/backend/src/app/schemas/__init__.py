"""接口请求与响应的数据结构。"""

# 将认证类导入当前包，允许其他模块通过 app.schemas 直接使用。
from app.schemas.auth import (
    LoginRequest, TokenResponse, UserCreate,
    SetupAdminRequest, UpdateProfileRequest,
    ChangePasswordRequest, UserResponse,
)

# 声明当前包对外提供的名称。
__all__ = [
    "LoginRequest", "TokenResponse", "UserCreate",
    "SetupAdminRequest", "UpdateProfileRequest",
    "ChangePasswordRequest", "UserResponse",
]