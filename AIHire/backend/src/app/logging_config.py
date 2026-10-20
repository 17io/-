
# ═══════════════════════════════════════════════════════════════
#     统一日志配置。
#   · Python logging 概念：任何模块里 logging.getLogger(__name__) 拿一个"记录器"往里写日志；
#     本文件的 setup_logging() 在应用启动时执行一次，决定日志"写到哪、什么格式、什么级别"。
#   · 双输出：控制台（开发时实时看）+ backend/logs/app.log（事后排查看）。
#   · 级别从低到高：DEBUG < INFO < WARNING < ERROR，由 .env 的 LOG_LEVEL 控制。
# ═══════════════════════════════════════════════════════════════
"""统一日志配置：同时输出到控制台和日志文件。

所有模块用 `logging.getLogger(__name__)` 获取 logger 即可，
本模块在应用启动时调用一次 setup_logging() 完成根 logger 配置。
"""

import logging  # Python 内置日志模块，负责记录和输出日志
import sys  # 这里使用 sys.stdout，把日志输出到终端的标准输出
from pathlib import Path

from app.config import settings  # 读取配置中的 LOG_LEVEL


# 记录本模块是否已经完成日志初始化。
# 初始为 False；配置成功后改成 True，避免重复添加输出通道。
_LOGGING_CONFIGURED = False


def setup_logging() -> None:
    """配置根 logger：控制台 + 文件双输出，级别由 LOG_LEVEL 控制"""

    # 声明下面使用的是模块级变量。
    # 后面对它赋值时，会修改上面定义的 _LOGGING_CONFIGURED。
    global _LOGGING_CONFIGURED

    # 同一个进程里，如果已经初始化过，就直接结束本次调用。
    if _LOGGING_CONFIGURED:
        return

    # 把配置中的级别名称转成大写，例如 "info" 转成 "INFO"。
    # 根据名称取得 logging 中的级别常量。
    # 如果名称不存在，就使用 INFO。
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # 不传入名称，取得的是根日志记录器。
    # 后面各模块的日志，通常会向上传递到这里统一输出。
    root = logging.getLogger()

    # 设置根日志记录器的级别。
    # 普通模块继承这个级别时，低于该级别的日志不会被记录。
    root.setLevel(level)

    # 定义一条日志的显示格式：
    # 时间 | 日志级别 | 记录器名称 | 日志内容
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ===== 控制台输出 =====

    # 创建一个输出到终端标准输出的日志处理器。
    console = logging.StreamHandler(sys.stdout)

    # 为控制台日志应用上面定义的格式。
    console.setFormatter(fmt)

    # 把控制台处理器交给根日志记录器。
    root.addHandler(console)

    # ===== 文件输出 =====

    # 当前文件位于 backend/src/app/logging_config.py。
    # parents[2] 指向 backend，在它下面使用 logs 目录。
    log_dir = Path(__file__).resolve().parents[2] / "logs"

    # 创建日志目录；已经存在时，不报错。
    log_dir.mkdir(exist_ok=True)

    # 创建文件处理器，将日志写入 backend/logs/app.log。
    # UTF-8 编码支持中文；默认使用追加模式，保留已有日志。
    file_handler = logging.FileHandler(
        log_dir / "app.log",
        encoding="utf-8",
    )

    # 文件日志使用与控制台相同的格式。
    file_handler.setFormatter(fmt)

    # 把文件处理器交给根日志记录器。
    root.addHandler(file_handler)

    # 两个输出通道配置完成，标记为已初始化。
    _LOGGING_CONFIGURED = True