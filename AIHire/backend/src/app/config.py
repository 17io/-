import os
from pathlib import Path  # 处理文件和文件夹路径
# BaseSettings 后面用它读取配置
# SettingsConfigDict 后面用它设置配置读取规则
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


def _find_root_env() -> str:
    """从当前文件位置向上查找项目根目录的 .env 文件
    backend/src/app/config.py → ../../../.env  （项目根）
    无论从哪个目录启动 uvicorn 都能找到同一份配置
    """
    # 把文件路径变成可操作对象.获取绝对值.获取文件所在文件夹
    p = Path(__file__).resolve().parent

    for _ in range(5):
        candidate = p / ".env"

        if candidate.exists():
            return str(candidate)

        p = p.parent

    return ".env"


class Settings(BaseSettings):
    """主后端配置：从环境变量和 .env 读取，未提供时使用默认值。"""

    # ===== 应用基本信息 =====
    APP_NAME: str = "智聘"  # 应用名称
    DEBUG: bool = False  # 是否输出调试信息；本地需要时再开启
    LOG_LEVEL: str = "INFO"  # 日志级别，例如 DEBUG、INFO、WARNING、ERROR

    # ===== 数据库连接 =====
    DATABASE_URL: str = "mysql+aiomysql://root:123456@localhost:3306/recruit_ai?charset=utf8mb4"  # 业务数据库连接地址；实际账号、密码和库名通过 .env 配置

    # ===== 大模型接口 =====
    LLM_PROVIDER: str = "openai"  # 使用 OpenAI 兼容接口方式
    OPENAI_API_KEY: Optional[str] = None  # 调用模型服务的密钥
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"  # 模型服务的接口基础地址
    OPENAI_MODEL: str = "gpt-4o"  # 调用的模型名称，需与实际服务匹配

    # ===== Dify 考试分析 =====
    DIFY_API_URL: str = "http://localhost/v1"  # Dify 接口基础地址，考试分析服务会在后面拼接具体路径
    DIFY_API_KEY: Optional[str] = None  # Dify 应用访问密钥；未配置时原服务使用模拟分析

    # ===== 文本向量模型与 Milvus =====
    EMBEDDING_MODEL: str = "shibing624/text2vec-base-chinese"  # 向量模型名称；实际需与调用方式和向量维度匹配
    MILVUS_HOST: str = "localhost"  # Milvus 服务地址；独立 RAG 服务还有自己的配置类
    MILVUS_PORT: str = "19530"  # Milvus 服务端口

    # ===== 简历评分分流阈值 =====
    SCORE_THRESHOLD_FAST_TRACK: float = 80.0  # 达到此分数进入面试排期
    SCORE_THRESHOLD_QUESTIONNAIRE: float = 60.0  # 未达快速通道但达到此分数时进入问卷通道
    SCORE_THRESHOLD_TALENT_POOL: float = 40.0  # 未达问卷通道但达到此分数时进入人才池

    # ===== 评分权重与评分分歧检查 =====
    SCORE_WEIGHTS_DEFAULT: dict = {"skill": 0.4, "experience": 0.4, "stability": 0.2}  # 通用权重：技能、经验、稳定性
    SCORE_WEIGHTS_BY_CATEGORY: dict = {  # 按岗位类别覆盖默认权重
        "市场主管": {"skill": 0.35, "experience": 0.4, "stability": 0.25},
        "采购主管": {"skill": 0.4, "experience": 0.4, "stability": 0.2},
        "食品研发工程师": {"skill": 0.45, "experience": 0.35, "stability": 0.2},
        "销售内勤": {"skill": 0.4, "experience": 0.4, "stability": 0.2},
        "城市经理": {"skill": 0.3, "experience": 0.4, "stability": 0.3},
        "大宗贸易销售": {"skill": 0.3, "experience": 0.4, "stability": 0.3},
        "俄语外贸业务员": {"skill": 0.35, "experience": 0.4, "stability": 0.25},
        "英语翻译（总秘）": {"skill": 0.4, "experience": 0.4, "stability": 0.2},
        "电商运营经理": {"skill": 0.35, "experience": 0.4, "stability": 0.25},
        "电商资深运营": {"skill": 0.4, "experience": 0.4, "stability": 0.2},
        "视频号商务BD": {"skill": 0.3, "experience": 0.4, "stability": 0.3},
    }
    SCORE_DIFF_ALERT_THRESHOLD: Optional[float] = 10.0  # 按你的要求设为 10 分；复核判断与暂停逻辑后续实现

    # ===== 邮件通知 =====
    SMTP_HOST: Optional[str] = None  # 邮件发送服务器地址
    SMTP_PORT: int = 587  # 邮件服务器端口
    SMTP_USER: Optional[str] = None  # 登录邮件服务器的账号
    SMTP_PASSWORD: Optional[str] = None  # 登录凭证，按邮箱服务要求填写密码或 SMTP 授权码
    NOTIFICATION_EMAIL_FROM: str = "noreply@recruitai.com"  # 发件人地址，实际使用时需配置有权发信的邮箱
    PUBLIC_BASE_URL: str = ""  # 邮件内链接使用的前端地址；原代码部分位置为空时回退到 localhost:5173

    # ===== Twilio 短信通知 =====
    TWILIO_ACCOUNT_SID: Optional[str] = None  # Twilio 账户标识
    TWILIO_AUTH_TOKEN: Optional[str] = None  # Twilio 访问凭证
    TWILIO_PHONE_NUMBER: Optional[str] = None  # 通过 Twilio 发送短信时使用的发信号码

    # ===== 企业微信机器人 =====
    WEWORK_WEBHOOK_URL: Optional[str] = None  # 企业微信群机器人的消息接收地址

    # ===== 钉钉通知与日历 =====
    DINGTALK_WEBHOOK_URL: Optional[str] = None  # 钉钉群机器人的消息接收地址
    DINGTALK_APP_KEY: Optional[str] = None  # 钉钉应用标识，用于日历集成
    DINGTALK_APP_SECRET: Optional[str] = None  # 钉钉应用密钥；原代码也将此字段用于机器人消息签名

    # ===== JWT 登录认证 =====
    JWT_SECRET: str = ""  # 登录令牌的签名密钥；正式启动 API 前必须配置
    JWT_ALGORITHM: str = "HS256"  # 令牌签名算法，不代表令牌内容被保密加密
    JWT_EXPIRE_HOURS: int = 24  # 默认登录令牌有效期，单位为小时

    # ===== 外部考试平台回调与答题看板同步 =====
    EXAM_WEBHOOK_TOKEN: Optional[str] = None  # 接收考试回调时核对的共享令牌；未配置则拒绝回调
    WORKMENUL_API_BASE: Optional[str] = None  # 答题看板接口基础地址；未配置则不启动周期同步
    EXAM_SYNC_INTERVAL_SECONDS: int = 60  # 每轮同步后的等待时间，单位为秒

    # ===== 面试默认参数：当前原项目尚未读取这三个字段 =====
    DEFAULT_INTERVIEW_DURATION: int = 60  # 预留的默认面试时长，单位为分钟
    MIN_INTERVAL_BETWEEN_INTERVIEWS: int = 15  # 预留的两场面试最小间隔，单位为分钟
    MAX_INTERVIEWS_PER_DAY: int = 5  # 预留的每日面试场次数量上限

    # ===== RabbitMQ 异步任务队列 =====
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"  # RabbitMQ 连接地址
    TASK_EXCHANGE: str = "recruit_tasks"  # 任务交换机名称，原实现使用 direct 类型
    TASK_QUEUE_NAME: str = "resume_analysis"  # 等待 worker 消费的任务队列名
    TASK_PREFETCH_COUNT: int = 8  # 单 worker 未确认消息上限，也用于流程执行并发控制
    TASK_MAX_RETRIES: int = 5  # 初次执行失败后，最多额外重试的次数
    TASK_RETRY_BACKOFF: float = 2.0  # 目标重试等待时间的指数计算基数
    TASK_RETRY_BACKOFF_MAX: float = 60.0  # 计算出的重试目标等待时间上限，单位为秒
    TASK_RATE_LIMIT_PER_MIN: int = 300  # 每分钟任务数参考值；当前尚未接入实际限速逻辑
    TASK_ENABLED: bool = True  # 是否启用队列；关闭时工作流接口直接执行流程

    # ===== Langfuse 模型调用观测 =====
    LANGFUSE_ENABLED: bool = False  # 是否尝试将接入追踪的模型调用记录上报到 Langfuse
    LANGFUSE_PUBLIC_KEY: Optional[str] = None  # Langfuse 项目 public key
    LANGFUSE_SECRET_KEY: Optional[str] = None  # Langfuse 项目 secret key
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"  # Langfuse 服务地址，也可配置为自建服务地址

    # ===== JD 全网参考搜索 =====
    JD_REF_ENABLED: bool = True  # 是否启用 JD 全网参考搜索功能
    JD_REF_BING_BASE: str = "https://cn.bing.com"  # Bing 搜索基础地址
    JD_REF_SEARCH_PROVIDERS: str = "sogou,bing_cn"  # 搜索渠道及尝试顺序，使用逗号分隔
    JD_REF_SEARCH_TIMEOUT: float = 10.0  # 单次搜索请求超时时间，单位为秒
    JD_REF_SEARCH_RETRIES: int = 1  # 单个搜索渠道失败后的额外重试次数
    JD_REF_MAX_RESULTS: int = 8  # 默认最多保留的外部参考结果数量
    JD_REF_FETCH_PAGE_BODY: bool = False  # 是否额外抓取搜索结果网页正文，默认关闭
    JD_REF_FETCH_PAGE_LIMIT: int = 3  # 启用正文抓取后，最多抓取的结果页数量
    JD_REF_FETCH_TIMEOUT: float = 5.0  # 单次网页正文请求超时时间，单位为秒
    JD_REF_USE_INTERNAL_KB: bool = False  # 生成 JD 参考材料时，是否追加内部知识库检索
    JD_REF_INTERNAL_KB_TIMEOUT: float = 8.0  # 内部知识库查询超时时间，单位为秒
    JD_REF_MAX_EXTRA_QUERY_CHARS: int = 60  # 参与构造搜索词的补充说明最大字符数，不是 token 数

    # 配置读取规则：查找 .env、按 UTF-8 读取、忽略未声明的额外字段
    model_config = SettingsConfigDict(
        env_file=_find_root_env(),  # 调用前面定义的函数，取得 .env 路径
        env_file_encoding="utf-8",  # 支持中文配置内容
        extra="ignore",  # 共用 .env 时，忽略不属于当前类的字段
    )


# 创建全局配置对象，其他模块通过 settings.字段名读取
settings = Settings()