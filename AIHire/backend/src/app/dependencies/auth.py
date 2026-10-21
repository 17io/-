# ═══════════════════════════════════════════════════════════════
# 认证三件套：
#   1. 密码：bcrypt 哈希存库，登录时 verify_password 比对
#   2. JWT：登录成功签发令牌；get_current_user 依赖校验请求头里的令牌并查出用户
#   3. 角色：在 Depends 中使用 require_role([UserRole.ADMIN])，未登录返回 401，角色不符返回 403
#   Depends(get_current_user) 尝试识别当前用户，失败时可以返回 None；强制登录与角色限制由 require_role 完成。
# ═══════════════════════════════════════════════════════════════
"""认证与权限依赖注入 — JWT 解析 + Role-Based Access Control

使用方式：
    # 在路由中获取当前用户
    @router.get("/candidates")
    async def list_candidates(current_user: User = Depends(get_current_user)):
        ...

    # 限制角色访问
    @router.post("/documents")
    async def create_document(_, current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.HR]))):
        ...
"""
from datetime import datetime, timedelta
import logging
from typing import List, Optional
# Depends 声明接口依赖；HTTPException 返回 HTTP 错误；status 提供状态码常量。
from fastapi import Depends, HTTPException, status
# 从请求头提取 Bearer 令牌；这里只提取字符串，JWT 验证在后面的函数中完成。
from fastapi.security import OAuth2PasswordBearer
# jwt 负责令牌签名与校验，JWTError 表示令牌校验异常。
from jose import JWTError, jwt
import bcrypt  # 第三方密码哈希工具，后续保存哈希结果而非明文密码
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User, UserRole

logger = logging.getLogger(__name__)

# ================================================================
# 密码工具
# ================================================================

# tokenUrl 声明登录接口地址；auto_error=False 表示缺少 Bearer 令牌时先返回 None。
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _to_bcrypt_bytes(password: str) -> bytes:
    """bcrypt 仅使用前 72 字节，超长时截断以保持哈希/校验一致"""
    # 将字符串编码为字节；这里的长度限制按 UTF-8 字节计算，不是字符数。
    data = password.encode("utf-8")
    # 保留原项目的超长密码截断规则，生成哈希和验证时使用同一规则。
    return data[:72] if len(data) > 72 else data


def hash_password(password: str) -> str:
    """密码哈希（bcrypt）"""
    # gensalt 生成随机盐；hashpw 计算哈希；decode 将哈希字节转成便于存库的字符串。
    return bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验密码"""
    try:
        # 使用输入密码和已保存的哈希进行比对，返回 True 或 False。
        return bcrypt.checkpw(_to_bcrypt_bytes(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError) as e:
        logger.debug("密码校验失败（哈希格式异常）: %s", e)
        return False


# ================================================================
# JWT 工具
# ================================================================


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT access token

    Args:
        data: 要编码的数据（至少包含 "sub" 字段）
        expires_delta: 过期时间，默认使用配置的 JWT_EXPIRE_HOURS

    Returns:
        JWT token 字符串
    """
    # 复制一份数据，添加过期时间时不修改调用方传入的原字典。
    to_encode = data.copy()
    # 优先使用传入的有效期；没有有效值时，使用 Settings 中配置的小时数。
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=settings.JWT_EXPIRE_HOURS))
    # exp 是 JWT 的过期时间字段；sub 通常保存登录用户名。
    to_encode.update({"exp": expire})
    # 使用配置的密钥和算法签名；签名用于校验完整性，不会加密隐藏载荷。
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """从 JWT token 解析当前用户

    如果 token 不存在或无效，返回 None（不报错，方便公开路由使用）。
    受保护的路由应使用 require_role() 代替。
    """
    # 没有令牌时保持原逻辑：返回 None，由调用方决定是否拒绝访问。
    if not token:
        return None
    try:
        # 验证签名、有效期等信息，并限定使用配置中的算法。
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError as e:
        logger.debug("JWT token 校验失败: %s", e)
        return None

    # 按令牌中的用户名查询当前数据库用户，后续角色检查使用数据库中的角色。
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    return user


def require_role(roles: List[UserRole]):
    """角色权限依赖：要求当前用户拥有指定角色之一

    Args:
        roles: 允许的角色列表

    Returns:
        与 Depends() 配合使用的依赖函数

    Raises:
        HTTPException 401/403: 未认证或权限不足

    Usage:
        @router.get("/api/documents")
        async def list_docs(current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.HR]))):
            ...
    """
    # 返回内部检查函数，FastAPI 执行接口前会先解析当前用户并调用它。
    async def _role_checker(current_user: Optional[User] = Depends(get_current_user)) -> User:
        # 未认证：返回 401，并告诉客户端使用 Bearer 认证。
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未认证，请先登录",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # 已有身份但角色不在允许列表：返回 403。
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要角色: {[r.value for r in roles]}",
            )
        return current_user
    return _role_checker
