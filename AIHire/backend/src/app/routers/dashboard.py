# 仪表盘提供候选人数量、状态分布和评分分桶统计。
# 评分权重更新只修改当前进程配置，不写入数据库。
"""仪表盘 API：招聘统计与评分权重管理。"""

from datetime import UTC, datetime, timedelta  # UTC 时区、日期时间和时间间隔。
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.models import Candidate, User, UserRole
from app.dependencies import require_role, get_current_user, candidate_scope_cond

router = APIRouter(
    prefix="/api/dashboard",  # 这组接口共同的地址前缀。
    tags=["仪表盘"],  # 自动接口文档中的分组名称。
    dependencies=[Depends(require_role([UserRole.ADMIN, UserRole.HR]))],  # 整组接口只允许管理员或 HR 访问。
)


@router.get("/stats")  # 与路由前缀组合，完整地址为 GET /api/dashboard/stats。
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),  # 获取本次请求的数据库会话。
    current_user: User = Depends(get_current_user),  # 根据请求携带的令牌识别当前用户。
):
    """获取仪表盘统计数据；HR 只统计自己名下的候选人，管理员统计全量。"""
    cond = candidate_scope_cond(current_user)  # 当前用户的数据范围条件；管理员得到 None。

    def _apply(stmt):
        """为查询语句统一附加当前用户的数据范围条件。"""
        return stmt.where(cond) if cond is not None else stmt

    # count 统计候选人 ID 的数量；_apply 保证统计范围符合当前用户权限。
    total = (await db.execute(_apply(select(func.count(Candidate.id))))).scalar() or 0

    # 按候选人状态分组，分别统计每个状态下的人数。
    status_result = await db.execute(
        _apply(select(Candidate.status, func.count(Candidate.id)))
        .group_by(Candidate.status)  # 将状态相同的候选人归为一组，再分别计数。
    )
    status_counts = dict(status_result.all())  # 取出全部统计行，转成“状态: 人数”的字典。

    # 以 UTC 当天零点为统计起点；数据库创建时间同样按不带时区标记的 UTC 值保存。
    today_start = datetime.now(UTC).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
    today_new = (await db.execute(
        _apply(
            select(func.count(Candidate.id))
            .where(Candidate.created_at >= today_start)  # 只统计从 UTC 当天零点起创建的记录。
        )
    )).scalar() or 0

    # 统计当前用户可见且已有匹配分的候选人，未评分记录不参与平均值计算。
    avg_score = (await db.execute(
        _apply(
            select(func.avg(Candidate.match_score))  # avg 由数据库计算匹配分的平均值。
            .where(Candidate.match_score.isnot(None))  # 排除数据库中的 NULL；0 分仍参与计算。
        )
    )).scalar() or 0  # 没有可计算的分数时，使用 0。

    # weekday() 返回周几：周一为 0，周日为 6；减去对应天数，得到本周周一的 UTC 零点。
    week_start = today_start - timedelta(days=today_start.weekday())
    trends = []  # 保存每天的日期和新增人数，供仪表盘展示本周趋势。
    for i in range(7):  # i 依次取 0～6，对应本周周一至周日。
        day = week_start + timedelta(days=i)  # 当前统计日的 UTC 零点。
        next_day = day + timedelta(days=1)  # 下一天零点，作为不包含在内的结束边界。
        count = (await db.execute(
            _apply(
                select(func.count(Candidate.id))
                .where(Candidate.created_at >= day)
                .where(Candidate.created_at < next_day)  # 使用左闭右开区间，避免零点记录被相邻两天重复统计。
            )
        )).scalar() or 0
        trends.append({  # append 向列表末尾追加一条每日统计结果。
            "date": day.strftime("%Y-%m-%d"),  # 将日期转换成 2026-10-24 这样的字符串。
            "count": count,
        })

    # 录取率（已决定候选人中的录用比例）
    interviewed = status_counts.get("interviewed", 0)  # 读取已面试人数；本公式未使用此变量。
    hired = status_counts.get("hired", 0)
    rejected = status_counts.get("rejected", 0)
    total_decided = hired + rejected  # 分母只包含已录用和已拒绝的人数。
    hire_rate = round(hired / total_decided * 100, 1) if total_decided > 0 else 0  # 百分比保留 1 位小数；无决定记录时为 0。

    return {
        "total_candidates": total,  # 当前用户可见的候选人总数。
        "today_new": today_new,  # 从 UTC 当天零点起创建的候选人数。
        "average_match_score": round(float(avg_score), 1),  # 平均匹配分，返回时保留 1 位小数。
        "hire_rate": hire_rate,  # 已决定记录中的录取比例，单位为百分比。
        "status_distribution": {  # 返回固定的状态名称；没有记录的状态补 0。
            "new": status_counts.get("new", 0),
            "analyzed": status_counts.get("analyzed", 0),
            "talent_pool": status_counts.get("talent_pool", 0),
            "q_sent": status_counts.get("q_sent", 0),
            "q_done": status_counts.get("q_done", 0),
            "scheduled": status_counts.get("scheduled", 0),
            "interviewed": status_counts.get("interviewed", 0),
            "hired": status_counts.get("hired", 0),
            "rejected": status_counts.get("rejected", 0),
            "archived": status_counts.get("archived", 0),
        },
        "weekly_trend": trends,  # 周一至周日共 7 条每日统计。
    }


# ========== v2 评分体系数据闭环 ==========

def _bucket_of(score: float, bucket_size: int = 10) -> int:
    """分数 → 分桶下界（75.3 → 70）"""
    # bucket_size 默认每档 10 分；// 是向下取整除法，75.3 // 10 得到 7.0。
    return int(score // bucket_size) * bucket_size


@router.get("/score-buckets")
async def get_score_buckets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分桶通过率报表 — 评分体系数据闭环的核心指标

    按总分 10 分一档统计面试结果（来源：supervisor 决策回流到
    resume.match_analysis.interview_outcome 的标签），输出：
    - 每档样本量 / 通过率
    - 相邻有效分档各至少 5 个样本，低分档通过率高出 10 个百分点以上时标记倒挂
    - 标注不足提示（样本 < 30 时只展示不建议）

    HR 仅统计自己名下候选人的标签样本；admin 全量。
    """
    from app.models import Resume

    query = select(Resume).join(Candidate, Resume.candidate_id == Candidate.id)  # 关联候选人表，以便按负责人限制简历范围。
    cond = candidate_scope_cond(current_user)
    if cond is not None:
        query = query.where(cond)
    result = await db.execute(query.where(Resume.match_analysis.isnot(None)))
    resumes = result.scalars().all()

    # 聚合：bucket → [total, passed]
    buckets: dict[int, list[int]] = {}
    labeled_total = 0  # 可用标注简历记录数；同一候选人的多份简历分别计数。
    for resume in resumes:
        ma = resume.match_analysis or {}  # 简历保存的匹配分析结果，空值按空字典处理。
        outcome = ma.get("interview_outcome")  # 只采纳 hired（录用）或 rejected（拒绝）标签。
        if outcome not in ("hired", "rejected"):
            continue  # 跳过本条无效或不完整的样本。
        score = ma.get("overall_score")
        if score is None:
            continue  # 跳过本条无效或不完整的样本。
        try:
            score = float(score)
        except (TypeError, ValueError):
            continue  # 跳过本条无效或不完整的样本。
        b = _bucket_of(score)  # 计算分档下界，例如 75.3 分归入下界 70。
        buckets.setdefault(b, [0, 0])  # 第一次遇到该分档时，初始化为 [样本数, 录用数]。
        buckets[b][0] += 1  # 该分档的样本数加 1。
        if outcome == "hired":
            buckets[b][1] += 1  # 录用样本数加 1；这里的通过指 hired。
        labeled_total += 1

    rows = []
    for b in sorted(buckets):  # 按分档下界从低到高整理结果。
        total, passed = buckets[b]
        rows.append({
            "bucket": f"{b}-{b + 9}",  # 分档显示名称，例如 70-79；小数分也按下界归档。
            "total": total,
            "passed": passed,  # 该分档中标签为 hired 的简历记录数。
            "pass_rate": round(passed / total * 100, 1) if total else 0,  # 该分档录用率，单位为百分比。
        })

    # 跨档倒挂检测：低分档通过率明显偏高 → 分数区分度存疑
    inversions = []
    for i in range(len(rows) - 1):
        lower, upper = rows[i], rows[i + 1]  # 比较相邻的非空分档，分档之间可能有空档。
        # 两档样本数均至少 5，且低档通过率严格高出 10 个百分点时记录倒挂。
        if lower["total"] >= 5 and upper["total"] >= 5 \
                and lower["pass_rate"] > upper["pass_rate"] + 10:
            inversions.append({
                "lower_bucket": lower["bucket"],
                "upper_bucket": upper["bucket"],
                "detail": f"{lower['bucket']} 通过率 {lower['pass_rate']}% "
                          f"高于 {upper['bucket']} 的 {upper['pass_rate']}%",
            })

    suggestions = []
    if labeled_total < 30:  # 样本不足时优先返回积累标签的提示；本接口不自动调整权重。
        suggestions.append(
            f"标注样本仅 {labeled_total} 条（<30），统计不显著，继续积累标签，暂不做任何调整"
        )
    elif inversions:
        suggestions.append(
            "检测到通过率倒挂：分数区分度存疑，建议检查对应分数段的维度分和权重"
        )
    else:
        suggestions.append("分桶单调性正常，暂无需调整")

    return {
        "labeled_total": labeled_total,
        "buckets": rows,
        "inversions": inversions,
        "suggestions": suggestions,
        "note": "标签来源：supervisor 决策回流。建议每周看一次，单变量调整。",
    }


@router.post("/scoring-weights", dependencies=[Depends(require_role([UserRole.ADMIN]))])
async def update_scoring_weights(
    payload: dict,  # JSON 请求体：weights 是权重字典，category 是可选的岗位类别。
    db: AsyncSession = Depends(get_db),
):
    """热更新评分权重（admin only，内存生效）

    接收 {"weights": {"skill": 0.4, "experience": 0.4, "stability": 0.2},
          "category": "python"（可选，缺省改默认）}
    - 校验通过后写入 settings（进程内存，立即对后续分析生效）
    - 重启后回退为 .env 配置，持久化请改 .env
    - 历史分数重算请另跑 scripts/recalc_scores.py
    """
    from fastapi import HTTPException
    weights = payload.get("weights")  # 例如 {"skill": 0.4, "experience": 0.4, "stability": 0.2}。
    category = payload.get("category")  # 提供有效非空值时修改该类别；否则修改通用权重。

    if not isinstance(weights, dict) or not weights:
        raise HTTPException(status_code=400, detail="weights 必须是非空字典")

    from app.workflow.scoring import _valid_weights  # 复用评分工具中的权重检查规则。
    if not _valid_weights(weights):
        raise HTTPException(
            status_code=400,
            detail="权重非法：所有权重必须 > 0 且求和 ≈ 1",
        )

    if category:
        by_cat = dict(settings.SCORE_WEIGHTS_BY_CATEGORY)  # 复制类别权重表，保留其他类别配置。
        by_cat[category] = weights
        settings.SCORE_WEIGHTS_BY_CATEGORY = by_cat  # 仅更新当前 Python 进程内存中的配置。
    else:
        settings.SCORE_WEIGHTS_DEFAULT = weights  # 不修改 .env，不重新计算历史分数。

    return {
        "applied": True,
        "scope": f"category={category}" if category else "default",
        "weights": weights,
        "warning": "已写入进程内存，重启后回退 .env；历史分数重算请跑 scripts/recalc_scores.py",
    }
