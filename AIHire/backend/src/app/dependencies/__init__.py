"""认证与权限相关依赖。"""

# 统一导出认证工具。
from app.dependencies.auth import (
    oauth2_scheme, hash_password, verify_password,
    create_access_token, get_current_user, require_role,
)

# 数据范围权限工具。
from app.dependencies.scope import (
    is_admin, candidate_visible_ids_subq,
    candidate_scope_cond, interview_scope_cond,
    ensure_candidate_visible, ensure_interview_visible, candidate_accessible,
)

__all__ = [
    "oauth2_scheme", "hash_password", "verify_password",
    "create_access_token", "get_current_user", "require_role",

    # 数据范围权限。
    "is_admin", "candidate_visible_ids_subq",
    "candidate_scope_cond", "interview_scope_cond",
    "ensure_candidate_visible", "ensure_interview_visible", "candidate_accessible",
]
