"""结构化日志——基于 structlog，统一 JSON/dev 格式输出"""

import structlog

# structlog.configure() 不可重复调用，第二次会污染已初始化的日志配置
_configured = False


def setup_logger() -> None:
    """初始化 structlog 全局配置（幂等）"""
    global _configured
    if _configured:
        return
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        # LoggerFactory 生成标准 logging.Logger，支持 disabled 属性和级别过滤
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取指定模块的结构化日志实例

    :param name: 日志名称，通常传入 __name__
    """
    setup_logger()
    return structlog.get_logger(name)
