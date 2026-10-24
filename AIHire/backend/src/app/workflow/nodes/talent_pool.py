# 人才池节点：将分流到这里的候选人写进 talent_pool 表，并更新候选人状态，
# 留待 HR 日后重新激活。默认分流区间为 40 分及以上、60 分以下；分数判断由图路由负责。
"""人才池节点"""

import logging  # 标准库：记录入池结果和数据库操作异常。
from ..state import RecruitmentState  # 招聘流程中传递的状态字典结构。
from ..utils import get_candidate  # 按候选人 ID 查询数据库记录的通用工具。
from app.database import async_session_factory  # 创建独立的异步数据库会话。
from app.models import TalentPool, TalentPoolStatus  # 人才池表模型，以及人才池记录的状态枚举。

logger = logging.getLogger(__name__)  # 以当前模块名创建日志器。


async def move_to_talent_pool_node(state: RecruitmentState) -> dict:
    """将候选人移入人才池并创建人才池记录"""
    candidate_id = state.get("candidate_id")  # 候选人编号，用于查询和关联人才池记录。
    match_score = state.get("match_score", 0)  # 入池时保存的匹配分；本节点不判断分数区间。
    position = state.get("position", "")  # 入池前应聘的岗位名称。
    analysis = state.get("analysis_result", {})  # 分析结果，读取其中的技能与优势。

    if not candidate_id:  # 缺少编号时立即返回，不创建数据库会话。
        return {"errors": ["缺少 candidate_id"]}

    async with async_session_factory() as db:
        try:
            from sqlalchemy import select

            candidate = await get_candidate(db, candidate_id)
            if not candidate:
                return {"errors": ["候选人不存在"]}

            existing = await db.execute(
                select(TalentPool).where(TalentPool.candidate_id == candidate_id)
            )
            if existing.scalar_one_or_none():  # 已有记录时不重复插入，也不覆盖旧的人才池资料。
                candidate.status = "talent_pool"
                await db.commit()
                logger.info("候选人 %s 已在人才池中，仅更新状态", candidate_id)
                return {
                    "status": "talent_pool",
                    "pipeline_stage": "talent_pool",
                }

            skills = candidate.tags or []  # 优先取得候选人现有标签，空值使用空列表。
            if analysis and isinstance(analysis, dict):
                skills = list(set(skills + analysis.get("skills", [])))  # 合并标签与分析技能后去重；set 不保留原列表顺序。

            strengths = []  # 候选人优势列表，默认没有。
            if analysis and isinstance(analysis, dict):
                match_analysis = analysis.get("match_analysis", {}) if isinstance(analysis, dict) else {}  # 取出嵌套的岗位匹配分析。
                strengths = match_analysis.get("strengths", []) if isinstance(match_analysis, dict) else []  # 嵌套内容是字典时才提取优势。

            pool_entry = TalentPool(
                candidate_id=candidate_id,
                original_position=position,  # 保存入池前应聘的岗位。
                match_score=match_score,
                strengths=strengths,
                pool_reason=f"匹配度{match_score}分，未达当前岗位要求但具备潜力",
                suitable_positions=[],  # 当前节点不推断适合的新岗位，先保存空列表。
                skills=skills,
                status=TalentPoolStatus.ACTIVE.value,  # 枚举转为 active 字符串，表示在池中等待机会。
            )
            db.add(pool_entry)
            await db.flush()  # 执行 INSERT 并取得人才池自增 ID，此时事务尚未提交。

            candidate.status = "talent_pool"
            candidate.talent_pool_id = pool_entry.id  # 将新人才池记录的编号回填到候选人。
            candidate.talent_pool_reason = pool_entry.pool_reason  # 同步保存入池原因。

            await db.commit()  # 将人才池记录和候选人修改一并提交。
            logger.info(
                "候选人 %s 已移入人才池 (pool_id=%s, score=%.1f)",
                candidate_id, pool_entry.id, match_score,
            )
        except Exception as e:
            await db.rollback()  # 失败时撤销当前事务中尚未提交的新增和修改。
            logger.error("候选人 %s 人才池创建失败: %s", candidate_id, e)
            return {
                "status": "talent_pool",
                "errors": [f"人才池创建失败: {str(e)}"],  # 返回错误列表；此分支中的 status 不能证明已成功入池。
            }

    return {
        "status": "talent_pool",
        "pipeline_stage": "talent_pool",
    }
