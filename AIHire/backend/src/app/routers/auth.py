# ═══════════════════════════════════════════════════════════════
# 认证模块：注册 / 登录 / 当前用户信息 / 改密码。
#   登录成功后发一个 JWT 令牌（一串经过签名的字符串），前端之后每次请求
#   在 Header 里带上它，后端用 dependencies/auth.py 的 get_current_user 验明正身。
#   登录接口负责核验账号密码，认证依赖负责识别后续请求中的用户。
# ═══════════════════════════════════════════════════════════════
"""认证 API — 注册 / 登录 / 当前用户 / 修改密码"""
import logging
from typing import List, Optional
# APIRouter 将同一类接口集中管理；Depends 声明执行接口前需要提供的依赖。
from fastapi import APIRouter, Depends, HTTPException, status
# select 构造查询；func 调用数据库聚合函数，例如统计管理员数量的 count。
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserRole
from app.schemas import (
    LoginRequest, TokenResponse, UserCreate, UserResponse,
    ChangePasswordRequest, SetupAdminRequest, UpdateProfileRequest,
)
from app.dependencies import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_role,
)

logger = logging.getLogger(__name__)

# prefix 是这组接口共同的路径前缀；tags 用于接口文档分组。
router = APIRouter(prefix="/api/auth", tags=["认证"])


# post 表示接收 POST 请求；response_model 限定响应字段；201 表示创建成功。
@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: UserCreate,  # 请求体按 UserCreate 校验，校验失败时返回 422。
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role([UserRole.ADMIN])),  # _ 表示不使用这个返回值，但管理员权限检查仍会执行。
):
    """由管理员创建 HR 或面试官账号。

    首个管理员只能通过 ``/api/auth/setup`` 创建；后续账号必须由已认证的
    管理员创建，避免公开注册接口被滥用。
    """
    # 管理员只能在此创建 HR 和 INTERVIEWER 角色
    if data.role not in (UserRole.HR, UserRole.INTERVIEWER):
        raise HTTPException(
            status_code=400,
            detail="自助注册仅支持 HR 或 interviewer 角色",
        )

    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建用户
    user = User(
        username=data.username,
        hashed_password=hash_password(data.password),  # 只保存 bcrypt 哈希，不保存明文密码。
        role=data.role.value,  # 将角色枚举转换成数据库保存的字符串。
        email=data.email,
        display_name=data.display_name,
    )
    db.add(user)  # 将新对象加入当前会话。
    await db.flush()  # 执行 INSERT，取得自增 ID；事务尚未提交。
    await db.refresh(user)  # 从数据库重新读取对象，补齐默认值等字段。
    # get_db 在请求成功结束时统一提交；发生异常时回滚。
    logger.info("管理员创建账号: username=%s role=%s", user.username, user.role)
    return user


@router.post("/setup", status_code=201)
async def setup_admin(data: SetupAdminRequest, db: AsyncSession = Depends(get_db)):
    """初始化系统管理员（仅当系统中无任何管理员时可用）

    首次部署时调用此端点创建第一个管理员账号。
    已有管理员后此端点将被禁用。
    """
    # 检查是否已存在管理员
    # scalar 直接取查询结果的第一个值；这里取得管理员数量。
    admin_count = await db.scalar(
        select(func.count(User.id)).where(User.role == UserRole.ADMIN.value)
    )
    if admin_count > 0:
        raise HTTPException(
            status_code=403,
            detail="系统已初始化，管理员已存在。请使用 /api/auth/login 登录。",
        )

    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建管理员
    user = User(
        username=data.username,
        hashed_password=hash_password(data.password),  # 只保存 bcrypt 哈希，不保存明文密码。
        role=UserRole.ADMIN.value,
        email=data.email,
    )
    db.add(user)  # 将新对象加入当前会话。
    await db.flush()  # 执行 INSERT，取得自增 ID；事务尚未提交。
    await db.refresh(user)  # 从数据库重新读取对象，补齐默认值等字段。
    # get_db 在请求成功结束时统一提交；发生异常时回滚。

    logger.info("系统初始化: 首个管理员已创建 username=%s", user.username)
    return {
        "message": "管理员创建成功",
        "username": user.username,
        "role": user.role,
    }


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录，返回 JWT token"""
    # 查找用户
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()  # 取唯一用户对象；没有匹配记录则为 None。

    # or 会短路：用户不存在时，不会访问 user.hashed_password。
    if not user or not verify_password(data.password, user.hashed_password):
        logger.warning("登录失败: username=%s (密码错误或用户不存在)", data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not user.is_active:
        logger.warning("登录被拒: username=%s (账号已禁用)", data.username)
        raise HTTPException(status_code=403, detail="账号已被禁用")

    # sub 保存用户名，role 保存签发时的角色；签名用于校验，不会加密隐藏这些字段。
    token = create_access_token(data={"sub": user.username, "role": user.role})
    logger.info("登录成功: username=%s role=%s", user.username, user.role)
    # token_type 使用 TokenResponse 中默认的 bearer，供客户端构造认证请求头。
    return TokenResponse(
        access_token=token,
        username=user.username,
        role=user.role,
    )


# get 表示读取信息；UserResponse 不包含密码哈希，避免把它返回给前端。
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未认证")
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    data: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        [UserRole.ADMIN, UserRole.HR, UserRole.INTERVIEWER]
    )),
):
    """更新当前用户资料（显示姓名 display_name；空串=清除并回退登录名）"""
    # exclude_unset=True：只保留请求中实际提交的字段，区分未提交和主动清空。
    updates = data.model_dump(exclude_unset=True)
    if "display_name" in updates:
        dn = (updates["display_name"] or "").strip()  # None 转为空串，再去掉首尾空白。
        current_user.display_name = dn or None  # 空串保存为 NULL，表示清除显示姓名。
    await db.flush()
    await db.refresh(current_user)
    logger.info("更新资料: username=%s display_name=%s", current_user.username, current_user.display_name)
    return current_user


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    role: Optional[str] = None,  # 查询参数，例如 /api/auth/users?role=hr；不是 JSON 请求体。
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.HR])),
):
    """列出可指派的用户（供候选人"负责人"下拉）。

    - admin：可传 ``?role=hr`` 等过滤；不传则返回全部启用用户。
    - HR：仅返回 HR 角色最小集（防通过列表接口遍历他人账号）。
    """
    query = select(User).where(User.is_active.is_(True))  # 只列出启用的账号。
    if current_user.role == UserRole.ADMIN.value:
        if role:
            query = query.where(User.role == role)
    else:
        # HR 只能看到同为 HR 的负责人候选（不含 admin/interviewer）
        query = query.where(User.role == UserRole.HR.value)
    query = query.order_by(User.id)  # 按用户 ID 升序排列。
    result = await db.execute(query)
    return result.scalars().all()  # 提取每一行中的 User 对象，组成列表。


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        [UserRole.ADMIN, UserRole.HR, UserRole.INTERVIEWER]
    )),
):
    """修改当前用户的密码（需提供旧密码验证）"""
    # 验证旧密码
    if not verify_password(data.old_password, current_user.hashed_password):
        logger.warning("修改密码失败: username=%s (旧密码错误)", current_user.username)
        raise HTTPException(status_code=400, detail="旧密码不正确")

    # 更新密码
    current_user.hashed_password = hash_password(data.new_password)  # 替换旧哈希；修改由 ORM 跟踪。
    await db.flush()

    logger.info("修改密码成功: username=%s", current_user.username)
    return {"message": "密码修改成功"}
