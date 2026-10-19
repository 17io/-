from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ===== 创建数据库引擎 =====

# 读取 config.py 中的数据库连接地址。
DB_URL = settings.DATABASE_URL

# 引擎负责管理数据库连接。
# 创建引擎时不会立刻连接 MySQL，真正执行数据库操作时才会建立连接。
engine = create_async_engine(
    DB_URL,
    echo=settings.DEBUG,  # DEBUG 开启时，输出执行的 SQL。
    pool_size=20,         # 连接池最多保留 20 条常驻连接，按需创建。
    max_overflow=40,      # 高峰期最多再临时增加 40 条连接。
    pool_pre_ping=True,   # 取出连接时先检查，避免使用已经断开的连接。
    pool_recycle=1800,    # 连接超过 1800 秒后，下次取用时更新。
    pool_timeout=30,      # 无可用连接时，最多等待 30 秒。
)


# ===== 创建会话工厂 =====

# 工厂负责生成会话，每次请求可以使用独立的会话。
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后，保留已加载的对象属性。
)


# ===== 定义数据模型的公共基类 =====

class Base(DeclarativeBase):
    """后续所有数据库模型都继承这个类。"""

    pass


# ===== 为接口提供数据库会话 =====

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """提供一个会话，并处理提交、回滚与关闭。"""

    async with async_session_factory() as session:
        try:
            # 把会话交给调用方使用。
            yield session

            # 调用方正常执行完毕后，提交本次修改。
            await session.commit()

        except Exception:
            # 发生异常时，撤销当前事务中尚未提交的修改。
            await session.rollback()

            # 继续抛出异常，交给上层处理。
            raise

        # 离开 async with 时，会自动关闭会话并归还连接。