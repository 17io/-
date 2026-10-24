# ═══════════════════════════════════════════════════════════════
# 评分 v2 的“计算器”：接收维度分，按配置的权重计算总分。
#   总分 = skill分×权重 + experience分×权重 + stability分×权重（权重可在 config 按岗位覆盖）。
#   亮点设计：某个维度缺失时不硬编 50 分，而是把剩余维度权重"重归一化"
#   （比如缺 stability 时 0.4/0.4/0.2 → 0.5/0.5），并返回 complete=False 供调用方判断。
# ═══════════════════════════════════════════════════════════════
"""综合评分计算（v2 评分体系第一期）

设计原则：
  1. LLM 只产维度分（客观证据），总分由本模块按权重计算（业务策略）
  2. 权重从 config 读取，可按岗位类别覆盖，改权重无需重跑 LLM
  3. 维度分缺失时不静默给 50 分：
     - 部分缺失 → 用已有维度按重归一化权重计算，标记 partial
     - 全部缺失 → 不产分，由调用方决定是否降级用 LLM 重评分
     凡是缺失场景 complete=False，上流路由不应自动分流，转人工复核
"""
import logging
from typing import Optional  # 可选类型，例如岗位类别可以是字符串或 None。

from app.config import settings  # 从统一配置对象读取默认权重和岗位权重。

logger = logging.getLogger(__name__)

# 维度名与子 Agent 输出字段的对应关系；实际提取逻辑见 extract_dimension_scores。
DIMENSION_FIELDS = {
    "skill": "skill_match_score",        # 来自技能 Agent
    "experience": "experience_score",    # 来自经验 Agent
    "stability": "stability_score",      # 稳定性分，取自经验分析结果
}

# 最后一道防线：config 里的默认权重本身非法时，用这份硬编码值兜底
_SAFE_DEFAULT_WEIGHTS = {"skill": 0.4, "experience": 0.4, "stability": 0.2}


def get_weights(category: Optional[str] = None) -> dict:
    """获取指定岗位类别的评分权重

    优先级：SCORE_WEIGHTS_BY_CATEGORY[category] > SCORE_WEIGHTS_DEFAULT
    合法性校验：权重必须全部 > 0 且求和 ≈ 1（容差 0.01），
    非法时回退硬编码安全默认值（而非 config 里可能同样非法的默认值）
    """
    weights = dict(settings.SCORE_WEIGHTS_DEFAULT)  # 复制配置字典，避免合并时直接修改默认配置。

    if category and settings.SCORE_WEIGHTS_BY_CATEGORY:
        override = settings.SCORE_WEIGHTS_BY_CATEGORY.get(category)  # 查找当前岗位的覆盖项；不存在时为 None。
        if override:
            weights.update(override)  # 按同名键覆盖，未指定的维度仍保留默认权重。

    if not _valid_weights(weights):
        logger.warning("岗位 %s 的权重配置非法（%s），回退安全默认权重", category, weights)
        weights = dict(_SAFE_DEFAULT_WEIGHTS)

    return weights


def _valid_weights(weights: dict) -> bool:
    # 下划线开头表示内部辅助函数；这里检查非空、可转数值、均为正数且总和接近 1。
    if not weights:
        return False
    try:
        values = [float(v) for v in weights.values()]  # 遍历字典中的权重，统一转成浮点数进行检查。
    except (TypeError, ValueError):
        return False
    if not values or any(v <= 0 for v in values):  # any：只要有一个权重不大于 0，就判为非法。
        return False
    return abs(sum(values) - 1.0) <= 0.01  # abs 取绝对值，允许权重和与 1 的差不超过 0.01。


def _to_score(value) -> Optional[float]:
    """把子 Agent 给的分转成 0-100 的 float，取不到/非法返回 None"""
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(100.0, score))  # 将可转换的分数限制在 0～100；负数变 0，超过 100 变 100。


def extract_dimension_scores(
    skills_analysis: dict, experience_analysis: dict
) -> dict:
    """从子 Agent 结果中提取三个维度分，缺失为 None"""
    raw = {
        "skill": skills_analysis.get("skill_match_score"),
        "experience": experience_analysis.get("experience_score"),
        "stability": experience_analysis.get("stability_score"),
    }
    return {dim: _to_score(val) for dim, val in raw.items()}  # 字典推导式：逐个转换维度分，缺失或转换失败为 None。


def compute_overall(
    dimension_scores: dict, weights: dict
) -> dict:
    """按权重计算综合分

    Returns:
        {
            "overall": float | None,     # 综合分；全部维度缺失时为 None
            "source": str,               # weighted / weighted_partial / llm_fallback / none
            "complete": bool,            # 三个维度是否齐全
            "missing": list,             # 缺失的维度名
            "weights_used": dict,        # 实际使用的权重（partial 时为重归一化后）
        }
    """
    # dimension_scores 是各维度分数；weights 是各维度权重。本函数不请求大模型、不写数据库。
    # overall：综合分；source：计算方式；complete：权重表内的维度是否都有分。
    # missing：缺失维度名；weights_used：本次计算使用的权重。
    scores = {}  # 只保存有分数的维度，值为 (分数, 数值权重)。
    for dim, weight in weights.items():  # items 同时取出维度名称和对应权重。
        score = dimension_scores.get(dim)
        if score is not None:  # 0 分是有效分数，不能用 if score 来判断是否缺失。
            scores[dim] = (score, float(weight))

    missing = [dim for dim in weights if dim not in scores]  # 只按传入的权重维度检查缺失。

    if not scores:  # 所有权重维度都缺失时返回无分，不凭空生成默认分数。
        return {
            "overall": None,
            "source": "none",
            "complete": False,
            "missing": list(weights.keys()),
            "weights_used": dict(weights),
        }

    if missing:
        # 部分缺失：按剩余维度重归一化权重（比如缺 stability 时 0.4/0.4 → 0.5/0.5）
        total_w = sum(w for _, w in scores.values())  # 汇总已有分数维度的权重；_ 表示不使用分数值。
        renormalized = {dim: w / total_w for dim, w in weights.items() if dim in scores}  # 重新分配后，已有维度的权重和为 1。
        overall = sum(s * renormalized[dim] for dim, (s, _) in scores.items())  # 各维度分数乘以重新分配的权重，再求和。
        return {
            "overall": round(overall, 1),  # 综合分保留 1 位小数。
            "source": "weighted_partial",
            "complete": False,
            "missing": missing,
            "weights_used": {k: round(v, 4) for k, v in renormalized.items()},
        }

    overall = sum(s * w for s, w in scores.values())  # 维度齐全时，直接按原权重计算加权总分。
    return {
        "overall": round(overall, 1),
        "source": "weighted",
        "complete": True,
        "missing": [],
        "weights_used": {k: float(v) for k, v in weights.items()},
    }
