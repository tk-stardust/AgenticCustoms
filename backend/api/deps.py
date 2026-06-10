"""FastAPI 依赖注入——管理 Agent 等资源的单例生命周期"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import select

from agents.hs_classifier.agent import HsClassifierAgent
from agents.tariff_calculator.agent import TariffCalculatorAgent
from data.db.database import async_session
from data.db.models import User
from shared.config import settings

_hs_agent: HsClassifierAgent | None = None
_tariff_agent: TariffCalculatorAgent | None = None
_bearer = HTTPBearer(auto_error=False)


def get_hs_agent() -> HsClassifierAgent:
    """获取 HS 归类 Agent 单例，避免每次请求重新创建"""
    global _hs_agent
    if _hs_agent is None:
        _hs_agent = HsClassifierAgent()
    return _hs_agent


def get_tariff_agent() -> TariffCalculatorAgent:
    """获取关税计算 Agent 单例，避免每次请求重新创建"""
    global _tariff_agent
    if _tariff_agent is None:
        _tariff_agent = TariffCalculatorAgent()
    return _tariff_agent


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> User | None:
    """从 JWT 解析当前用户，未登录返回 None"""
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
    except JWTError:
        return None
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def require_user(user: User | None = Depends(get_current_user)) -> User:
    """获取当前用户，未登录则 401"""
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return user
