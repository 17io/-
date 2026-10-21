"""认证与权限相关依赖。"""

# 本轮先导出认证工具，数据范围权限工具将在后续模块补齐。
from app.dependencies.auth import (
    oauth2_scheme, hash_password, verify_password,
    create_access_token, get_current_user, require_role,
)

__all__ = [
    "oauth2_scheme", "hash_password", "verify_password",
    "create_access_token", "get_current_user", "require_role",
]
