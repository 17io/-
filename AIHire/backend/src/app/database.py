from collections.abc import AsyncGenerator  # 用于类型标注，表示函数会异步地通过 yield 提供数据

# AsyncSession：异步数据库会话，通过它执行查询、添加、修改、删除等操作。
# async_sessionmaker：会话工厂，负责创建 AsyncSession。
# create_async_engine：创建异步数据库引擎，管理数据库连接。
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase  # 用来定义所有数据模型共同继承的父类
from app.config import settings

# ===== 创建数据库引擎 =====

# 读取 config.py 中的数据库连接地址。
DB_URL = settings.DATABASE_URL

# 引擎负责管理数据库连接。
# 创建引擎时不会立刻连接 MySQL，真正执行数据库操作时才会建立连接。
engine = create_async_engine(
    DB_URL,
    echo=settings.DEBUG,  # DEBUG 开启时，输出执行的 SQL。
    pool_size=20,  # 连接池最多保留 20 条常驻连接，按需创建。
    max_overflow=40,  # 高峰期最多再临时增加 40 条连接。
    pool_pre_ping=True,  # 取出连接时先检查，避免使用已经断开的连接。
    pool_recycle=1800,  # 连接超过 1800 秒后，下次取用时更新。
    pool_timeout=30,  # 无可用连接时，最多等待 30 秒。
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
    """所有 ORM 模型的基类。

    models/ 目录下的每个 class Xxx(Base) 都继承它，
    SQLAlchemy 靠这个继承关系把"Python 类"登记成"数据库表"。
    """

    pass


# ===== 为接口提供数据库会话 =====

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：每个需要数据库的接口自动获得一个会话

    在 router 文件里会看到函数参数写成：
    db: AsyncSession = Depends(get_db)
    意思是：调用这个接口时，FastAPI 自动执行 get_db() 并把会话传进来。
    本函数用 yield 实现了"自动收尾"：
      - 请求处理成功 → 自动 commit（把改动写进数据库）
      - 处理中抛异常 → 自动 rollback（撤销本次所有改动，防止写脏数据）
      - 无论成败     → 最后自动 close（把连接还给池子）
    路由代码只管写业务逻辑，完全不用操心这些。
    """

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


# ===== 初始化数据库表 =====

# ===== 初始化数据库表 =====

async def init_db() -> None:
    """根据已登记的模型，在数据库中创建缺失的表。"""

    # 执行 models/__init__.py，导入全部模型并登记表结构。
    import app.models

    # 从引擎取得连接，进入数据库操作上下文。
    async with engine.begin() as conn:
        # 通过异步连接调用 SQLAlchemy 的同步建表入口。
        await conn.run_sync(Base.metadata.create_all)
