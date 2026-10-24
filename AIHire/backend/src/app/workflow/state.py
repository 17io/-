"""RecruitmentState — LangGraph 全程共用的状态对象

    可以把 RecruitmentState 想象成一张"候选人审批流转单"：
    工作流里的每个节点（解析简历、AI 分析、分流、排面试……）都拿着同一张单子，
    处理完自己在上面填几个字段，再把单子传给下一个节点。
    本文件只定义"单子上有哪些栏位"（数据结构），不含任何业务逻辑。

LangGraph 三句话入门：
1. 一条招聘流水线 = 一个"图"（graph.py），流水线上每个工位 = 一个"节点"（nodes/ 目录）。
2. 节点之间传递的就是这里定义的 State 字典。
3. 每个节点函数的返回值是一个 dict，LangGraph 自动把它 merge（合并）回 State，
   所以下一个节点立刻能看到上一个节点写了什么。

为什么用 TypedDict 而不是普通 dict？
    TypedDict 只是"带类型标注的 dict"，运行时和 dict 完全一样，
    好处是 IDE 能自动提示字段名、拼错字段会有黄色警告。
    total=False 表示所有字段都是可选的——毕竟刚进流水线时大部分栏位还是空的。

多 Agent 并行的关键：
    "3 路并行分析"会同时跑 3 个节点，它们各自只写自己专属的 key
    （basic_info_analysis / skills_analysis / experience_analysis），
    互不覆盖；最后由汇总节点 synthesize_analysis_node 读取三者合并出总分。
"""

from typing import TypedDict, Optional, List, Annotated  # Python 标准库提供的类型标注工具。
from langgraph.graph.message import add_messages  # LangGraph 的消息合并函数，按消息 ID 追加或更新。


class RecruitmentState(TypedDict, total=False):
    """招聘流程中传递的状态字典；所有字段的键都允许暂时不提供。"""

    # 候选人基本信息。
    candidate_id: int  # 候选人在数据库中的 ID，用于定位相关记录。
    candidate_name: str  # 候选人姓名，用于组装分析提示词等。
    position: str  # 应聘岗位，用于岗位标准匹配和评分权重选择。
    email: str  # 候选人邮箱，供通知逻辑使用。
    phone: Optional[str]  # 候选人手机号；值可以是字符串或 None。

    # ============ 流程定位：现在走到哪一步了 ============
    status: str          # 状态机：new → parsed → classified → analyzed → ... → hired/rejected
    pipeline_stage: str  # 大阶段：resume(简历) / questionnaire(问卷) / interview(面试) / decision(决策)

    # ============ 简历 ============
    resume_text: Optional[str]        # 从 PDF/Word 提取出来的纯文本（解析节点的产物）
    job_description: Optional[str]    # 该岗位的 JD，用来和简历做匹配度对比

    # ============ 岗位分类 ============
    job_category: Optional[str]        # 岗位类别（如 销售/研发/运营），决定用哪套评分权重
    category_confidence: Optional[float]  # 分类置信度，业务约定为 0～1；类型标注本身不校验范围。

    # ============ AI 分析结果（3 个子 Agent 产物 + 综合）============
    analysis_result: Optional[dict]             # 汇总后的分析字典，供调用方保存或展示。
    match_analysis: Optional[dict]              # 与 JD 的匹配分析
    match_score: Optional[float]                # 最终匹配总分 0~100（分流就按它判定）
    basic_info_analysis: Optional[dict]         # 基本信息分析结果，如姓名、联系方式和学历等。
    skills_analysis: Optional[dict]             # 子 Agent 2：技能分析（含 skill_match_score 维度分）
    experience_analysis: Optional[dict]         # 子 Agent 3：经验分析（含 experience_score、stability_score）

    # ============ 评分体系 v2（维度分派生总分 + 双通道留痕）============
    # 设计思想：LLM 只负责给"维度分"（有客观证据支撑），总分由 scoring.py 按权重算出来。
    # 这样调权重不用重新花钱跑 LLM，历史候选人也能批量重算。
    analysis_complete: Optional[bool]    # 维度分是否齐全，供调用方判断能否自动分流。
    llm_overall_score: Optional[float]   # LLM 给出的综合重评分，用于留痕及与加权分比较。
    score_diff: Optional[float]          # 加权分与 LLM 重评分的绝对差；字段本身不执行阈值判断。

    # ============ 问卷（走问卷通道时才有值）============
    questionnaire_id: Optional[int]        # 问卷记录的数据库 ID
    questionnaire_status: Optional[str]    # sent / completed / expired
    questionnaire_score: Optional[float]   # 问卷评分结果，由业务逻辑写入。
    questionnaire_passed: Optional[bool]   # 问卷是否通过，由业务逻辑设置。

    # ============ 面试 ============
    interview_id: Optional[int]           # 面试记录的数据库 ID
    interview_status: Optional[str]       # 见 models/interview.py 的状态枚举
    interview_decision: Optional[str]     # 面试最终结论：pass / reject
    interview_feedback: Optional[str]     # 面试官反馈原文（评审节点的输入）

    # ============ 面试评审（3 路并行评审 + supervisor 决策）============
    technical_review: Optional[dict]      # 评审 Agent 1：技术能力
    communication_review: Optional[dict]  # 评审 Agent 2：沟通表达
    culture_review: Optional[dict]        # 评审 Agent 3：文化匹配
    review_results: Optional[dict]        # 三路汇总
    decision_reason: Optional[str]        # supervisor 给出的录用/拒绝理由
    decision_confidence: Optional[str]    # 决策置信度（high / medium / low）
    risk_warning: Optional[str]           # 风险提示（如"频繁跳槽""技能与岗位不符"）

    # ============ Function Calling（自然语言查库/发邮件等工具调用）============
    fc_query: Optional[str]        # 用户的自然语言指令，如"查一下上周面试通过的人"
    fc_result: Optional[str]       # 工具执行结果（转成文字）
    fc_tool_calls: Optional[list]  # LLM 决定调用哪些工具的原始记录
    fc_response: Optional[str]     # LLM 基于工具结果生成的最终回答

    # ============ 流程控制 ============
    errors: List[str]                   # 错误信息列表；未配置累加规则，新值会替换旧列表。
    retry_count: int                    # 保存重试次数；字段定义不会自动执行重试。
    notifications_sent: List[str]       # 已发送通知的标识列表；防重复发送由发送逻辑负责。

    # ============ LangGraph 内置 ============
    # Annotated 为 list 附加 add_messages 合并规则，供 LangGraph 更新状态时使用。
    # 新 ID 的消息追加，同 ID 的消息更新已有记录，并非每次都只追加。
    # 普通字段通常用新值替换旧值；同一步并行写入同一普通字段会发生冲突。
    messages: Annotated[list, add_messages]
