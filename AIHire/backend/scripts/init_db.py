"""手动初始化练习数据库中的业务表。"""

import asyncio
import sys
from pathlib import Path

# 将 backend/src 加入模块查找路径，确保能够导入 app。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.database import engine, init_db


async def main() -> None:
    """执行建表，并在结束时释放数据库连接。"""

    try:
        # 调用之前定义的初始化函数，真正执行建表。
        await init_db()
        print("数据库表初始化完成")

    finally:
        # 无论成功或失败，都在事件循环结束前释放连接池。
        await engine.dispose()


# 直接运行本文件时，启动事件循环并执行 main。
if __name__ == "__main__":
    asyncio.run(main())