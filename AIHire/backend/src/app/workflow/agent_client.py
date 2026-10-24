# 工作流调用独立 Agent 的轻量封装：统一读地址配置、组装请求、读取响应，
# 各节点不用重复编写 HTTP 调用代码。
"""Agent HTTP 客户端

依赖注入：
  __init__ 可接受 httpx.AsyncClient 和各 Agent URL。
  未传入时回退到 env 变量 / 默认值（兼容旧代码）。
"""

import os  # 标准库：读取环境变量中的 Agent 服务地址。
import logging  # 标准库：记录调用失败等运行信息。
import httpx  # 第三方 HTTP 客户端，用于请求独立的 Agent 服务。
from typing import Optional  # 类型标注：参数或返回值允许为 None。

logger = logging.getLogger(__name__)  # 使用当前模块名创建日志器。


class AgentClient:
    """统一封装对各独立 Agent 的 HTTP 调用，支持由外部传入依赖。"""

    def __init__(
        self,
        httpx_client=None,  # 外部传入的 HTTP 客户端；None 表示没有提供。
        resume_parser_url: Optional[str] = None,  # 简历解析服务地址。
        classifier_url: Optional[str] = None,  # 岗位分类服务地址。
        notification_url: Optional[str] = None,  # 通知服务地址。
        analyzer_base_url: Optional[str] = None,  # 分析服务基础地址的配置值。
        port_map: Optional[dict] = None,  # 岗位类别到端口的映射，例如 {"python": "18008"}。
    ):
        """保存客户端和地址配置；初始化时不发送 HTTP 请求。"""
        self._httpx_client = httpx_client  # 将传入的客户端保存到当前对象。
        self.resume_parser_url = resume_parser_url or os.getenv("RESUME_PARSER_URL", "http://localhost:18001")
        self.classifier_url = classifier_url or os.getenv("CLASSIFIER_URL", "http://localhost:18002")
        self.notification_url = notification_url or os.getenv("NOTIFICATION_URL", "http://localhost:18006")
        self.analyzer_base_url = analyzer_base_url or os.getenv("ANALYZER_BASE_URL", "http://localhost:18008")
        self._port_map = port_map  # 保存外部传入的端口映射，不在这里生成默认映射。

    def _get_client(self, timeout: int = 30):  # timeout 是新建客户端的超时配置，单位为秒，默认 30。
        """获取 HTTP 客户端：优先使用外部传入的对象，否则临时创建。"""
        if self._httpx_client is not None:
            return self._httpx_client  # 直接返回已有对象，不修改它的超时配置。
        return httpx.AsyncClient(timeout=timeout)  # 没有外部客户端时，创建异步 HTTP 客户端。

    def _analyzer_url(self, category: str) -> str:  # category 是岗位类别标识，例如 python、java。
        """获取对应岗位的分析 Agent 地址。"""
        ports = self._port_map or {  # 优先使用非空的外部映射；没有时使用整份默认映射。
            "python": "18008", "java": "18009", "product": "18010",
            "ai": "18011", "frontend": "18012", "ops": "18013", "test": "18014",
            "erp": "18008", "外贸运营": "18008", "数据分析": "18008",
            "项目管理": "18008", "销售": "18008", "人力资源": "18008",
        }
        port = ports.get(category, "18008")  # 当前映射中找不到该类别时，使用端口 18008。
        return f"http://localhost:{port}"  # 将选中的端口拼入地址；本方法未读取 analyzer_base_url。

    async def parse_resume(self, file_content: bytes, filename: str) -> Optional[dict]:
        """调用 Resume Parser Agent 解析简历。"""
        # file_content 是文件的二进制内容；filename 是文件名，例如 resume.pdf。
        try:
            async with self._get_client(timeout=60) as client:  # 获取客户端；新建时使用 60 秒超时配置，退出时关闭。
                files = {"file": (filename, file_content)}  # 上传表单字段名是 file，元组依次保存文件名和内容。
                resp = await client.post(f"{self.resume_parser_url}/api/parse", files=files)  # 以文件表单发送 POST 请求。
                resp.raise_for_status()  # 非成功 HTTP 状态会抛出异常，交给下面的 except 处理。
                return resp.json()  # 将响应中的 JSON 文本解析成 Python 数据。
        except Exception as e:
            logger.warning("简历解析 Agent 调用失败: %s", e)
            return None  # 请求或响应处理失败时返回 None，由调用方决定如何处理。

    async def classify(
        self,
        resume_text: str,  # 已提取出的简历纯文本。
        position: str = "",  # 应聘岗位，未提供时使用空字符串。
        skills: Optional[list] = None,  # 已知技能列表，例如 ["Python", "MySQL"]，可以不提供。
    ) -> Optional[dict]:
        """调用 Classifier Agent 判断岗位类别。"""
        try:
            async with self._get_client(timeout=30) as client:
                resp = await client.post(
                    f"{self.classifier_url}/api/classify",
                    json={  # 将字典作为 JSON 请求体发送。
                        "resume_text": resume_text[:5000],  # 只发送前 5000 个字符；这里按字符截取，不是 Token。
                        "position": position,
                        "skills": skills or [],  # 没有提供技能时，发送空列表。
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning("岗位分类 Agent 调用失败: %s", e)
            return None

    async def analyze(
        self,
        category: str,  # 岗位类别，例如 python、java，用来选择分析服务地址。
        resume_text: str,  # 已提取的简历纯文本。
        job_description: str = "",  # 岗位描述（JD），未提供时使用空字符串。
    ) -> Optional[dict]:
        """调用对应岗位的分析 Agent。"""
        try:
            base = self._analyzer_url(category)  # 使用岗位端口映射生成分析服务基础地址。
            async with self._get_client(timeout=120) as client:  # 新建客户端时使用 120 秒超时配置。
                resp = await client.post(
                    f"{base}/api/analyze",
                    json={
                        "resume_text": resume_text[:15000],  # 发送前 15000 个字符，不修改原始简历文本。
                        "job_description": job_description,  # 将岗位要求一并交给分析服务。
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning("分析 Agent 调用失败 (category=%s): %s", category, e)
            return None


    async def send_notification(
        self,
        template: str,  # 通知模板标识，例如 interview_invite。
        channel: str,  # 发送渠道标识，例如 email；具体支持哪些渠道由通知服务决定。
        recipient: str,  # 接收目标，例如邮箱地址，具体格式取决于发送渠道。
        context: dict,  # 填充模板所需的数据，例如候选人姓名、岗位和面试时间。
    ) -> Optional[dict]:
        """调用 Notification Agent 发送通知。"""
        try:
            async with self._get_client(timeout=30) as client:
                resp = await client.post(
                    f"{self.notification_url}/api/send",
                    json={
                        "template": template,
                        "channel": channel,
                        "recipient": recipient,
                        "context": context,
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning("通知 Agent 调用失败 (template=%s): %s", template, e)
            return None


# 模块级共享实例：不传入参数，地址按环境变量或默认值确定；创建对象时不请求服务。
agent_client = AgentClient()
