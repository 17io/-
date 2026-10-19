# ═══════════════════════════════════════════════════════════════
#   异步任务进度表——RabbitMQ 队列方案的"进度看板"。
#   简历分析任务入队时创建一行，worker 每推进一步就更新 progress/status，
#   前端轮询 get_task_progress 接口就能画出进度条。
# ═══════════════════════════════════════════════════════════════
"""异步任务进度模型 — 记录每个异步分析任务的生命周期（配合 RabbitMQ 队列）

为什么需要它：
  - 任务入队后脱离 HTTP 请求，前端无法再从同步返回值拿结果
  - 这张表充当「进度公告板」：worker 每推进一个阶段就更新，前端轮询 GET /api/workflow/task/{task_id}
  - 同时是任务去重 / 审计 / 失败重放的依据

状态机： pending → received → running → success | failure
"""

import enum

# Index：显式定义索引，可将多个字段组成一个联合索引。
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Index, func
from app.database import Base

class TaskStatus(str, enum.Enum):
    """分析任务状态（字符串枚举：兼容 .value 取值与直接落库两种写法）"""
    PENDING = "pending"    # 等待处理。
    RECEIVED = "received"  # Worker 已领取。
    RUNNING = "running"    # 正在执行。
    SUCCESS = "success"    # 执行成功。
    FAILURE = "failure"    # 执行失败。

class TaskProgress(Base):
    """保存一项异步任务的最新进度。"""
    __tablename__ = "task_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 队列任务编号，由后续发布任务的代码生成并传入。
    task_id = Column(String(64), unique=True, index=True, nullable=False)

    # 任务所属候选人；同一候选人可以有多次分析任务。
    candidate_id = Column(Integer, ForeignKey("candidates.id"), index=True, nullable=False)

    # 默认等待处理，后续由 Worker 更新。
    status = Column(String(20), default=TaskStatus.PENDING.value, nullable=False, index=True)

    # 进度百分比，业务代码按阶段填写。
    progress = Column(Integer, default=0)

    # 程序使用的阶段标识，例如 parse_resume。
    current_stage = Column(String(40), default="")

    # 供使用者阅读的阶段描述，例如“开始解析简历”。
    stage_message = Column(String(255), default="")

    # 最终结果，例如候选人状态、匹配分数和岗位分类。
    result_payload = Column(JSON, default=None)

    # 失败或重试时记录的错误信息。
    error = Column(Text, default=None)

    # 已重试次数，由 Worker 的重试逻辑更新。
    retries = Column(Integer, default=0)

    # 创建和更新时间，由数据库时间表达式提供。
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 支持按候选人及任务状态组合查询。
    __table_args__ = (
        Index("ix_task_progress_candidate_status", "candidate_id", "status"),
    )

    def to_dict(self) -> dict:
        """将任务进度转换为接口可返回的字典。"""

        return {
            "task_id": self.task_id,
            "candidate_id": self.candidate_id,
            "status": self.status,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "stage_message": self.stage_message,

            # 对外返回 result，数据库字段仍叫 result_payload。
            "result": self.result_payload,

            "error": self.error,
            "retries": self.retries,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }