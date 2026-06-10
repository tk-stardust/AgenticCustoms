"""前端页面路由——每个 Vue Router 路径对应一个路由，刷新时不 404"""

import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["pages"])

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "dist")


@router.get("/favicon.png")
async def favicon():
    return FileResponse(os.path.join(FRONTEND_DIR, "favicon.png"))


def _index() -> FileResponse:
    """返回 Vue SPA 入口 HTML"""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@router.get("/")
async def home():
    """首页——HS 编码归类"""
    return _index()


@router.get("/classify")
async def classify_page():
    """HS 编码归类"""
    return _index()


@router.get("/compliance")
async def compliance_page():
    """合规校验"""
    return _index()


@router.get("/tariff")
async def tariff_page():
    """关税计算"""
    return _index()


@router.get("/login")
async def login_page():
    """登录"""
    return _index()


@router.get("/register")
async def register_page():
    """注册"""
    return _index()


@router.get("/chat")
async def chat_page():
    """AI 助手"""
    return _index()


@router.get("/pipeline")
async def pipeline_page():
    """一键全流程"""
    return _index()


@router.get("/dashboard")
async def dashboard_page():
    """风险看板"""
    return _index()


@router.get("/history")
async def history_page():
    """历史记录"""
    return _index()
