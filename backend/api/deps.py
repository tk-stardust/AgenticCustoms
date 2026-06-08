"""FastAPI 依赖注入——管理 Agent 等资源的单例生命周期"""

from agents.hs_classifier.agent import HsClassifierAgent

_hs_agent: HsClassifierAgent | None = None


def get_hs_agent() -> HsClassifierAgent:
    """获取 HS 归类 Agent 单例，避免每次请求重新创建"""
    global _hs_agent
    if _hs_agent is None:
        _hs_agent = HsClassifierAgent()
    return _hs_agent
