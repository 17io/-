# 工作流的小工具函数集合（候选人查询、数据库会话管理），被多个节点复用。
"""工作流节点通用工具 — 数据库会话管理、候选人查询等"""

from contextlib import asynccontextmanager  # 标准库：将异步生成器包装成可用于 async with 的上下文管理器。
from typing import Optional, AsyncGenerator  # 可空类型，以及异步生成器的类型标注。
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory  # 数据库会话工厂，用于创建独立的异步会话。
from app.models import Candidate  # 候选人数据库模型，用来构造查询。


async def get_candidate(db: AsyncSession, candidate_id: int) -> Optional[Candidate]:
    """按 ID 查询候选人，不存在返回 None"""
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    return result.scalar_one_or_none()  # 返回唯一候选人对象；找不到时返回 None，不自动抛出 404。


@asynccontextmanager
async def candidate_session(
    candidate_id: int,  # 需要查询的候选人 ID。
    suppress_errors: bool = False,  # 是否在回滚后不重新抛出普通异常，默认 False。
) -> AsyncGenerator[tuple[AsyncSession, Optional[Candidate]], None]:  # yield 提供 (会话, 候选人)；None 表示不接收 send 传入的数据。
    """上下文管理器：自动处理 开会话 → 查候选人 → 提交/回滚

    Args:
        candidate_id: 候选人 ID
        suppress_errors: True 时吞掉异常不抛出（用于非关键操作）

    Yields:
        (db_session, candidate) 元组

    用法:
        async with candidate_session(candidate_id) as (db, candidate):
            if candidate:
                candidate.status = "classified"
    """
    async with async_session_factory() as db:  # 创建独立会话，离开上下文时自动关闭。
        try:
            candidate = await get_candidate(db, candidate_id)  # 只按 ID 查找，不在这里检查用户角色或归属。
            yield db, candidate  # 将控制权交给调用方的 async with 代码块。
            await db.commit()  # 调用方代码块正常结束后，提交本次修改。
        except Exception:  # 处理查询、调用方代码块或提交过程中抛出的普通异常。
            await db.rollback()  # 撤销本次事务中尚未提交的修改。
            if not suppress_errors:
                raise  # 默认继续抛出原异常，让上层感知失败。
