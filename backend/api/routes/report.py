"""申报文件预览接口（报关单 / 原产地证 / 合规声明 三份文档的 HTML 预览）"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from data.db.database import async_session
from data.db.models import Declaration
from api.routes.pipeline import _build_customs_html, _build_origin_html, _build_compliance_html

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/pipeline/report/{request_id}/customs", response_class=HTMLResponse)
async def preview_customs(request_id: str):
    async with async_session() as session:
        result = await session.execute(select(Declaration).where(Declaration.request_id == request_id))
        decl = result.scalar_one_or_none()
    if not decl or not decl.results:
        raise HTTPException(404, "记录不存在")
    return HTMLResponse(content=_build_customs_html(decl.results))


@router.get("/pipeline/report/{request_id}/origin", response_class=HTMLResponse)
async def preview_origin(request_id: str):
    async with async_session() as session:
        result = await session.execute(select(Declaration).where(Declaration.request_id == request_id))
        decl = result.scalar_one_or_none()
    if not decl or not decl.results:
        raise HTTPException(404, "记录不存在")
    return HTMLResponse(content=_build_origin_html(decl.results))


@router.get("/pipeline/report/{request_id}/compliance", response_class=HTMLResponse)
async def preview_compliance(request_id: str):
    async with async_session() as session:
        result = await session.execute(select(Declaration).where(Declaration.request_id == request_id))
        decl = result.scalar_one_or_none()
    if not decl or not decl.results:
        raise HTTPException(404, "记录不存在")
    return HTMLResponse(content=_build_compliance_html(decl.results))
