"""申报历史记录接口"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, desc, delete

from data.db.database import async_session
from data.db.models import Declaration
from shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def list_history(limit: int = 20):
    """查询最近的申报记录

    :param limit: 返回条数上限
    """
    async with async_session() as session:
        result = await session.execute(
            select(Declaration)
            .order_by(desc(Declaration.created_at))
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "request_id": r.request_id,
                "commodity_name": r.commodity_name,
                "commodity_description": r.commodity_description,
                "hs_code": r.hs_code,
                "target_country": r.target_country,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "results": r.results,
            }
            for r in rows
        ]


@router.delete("/history/{record_id}")
async def delete_record(record_id: int):
    """删除指定申报记录"""
    async with async_session() as session:
        result = await session.execute(
            select(Declaration).where(Declaration.id == record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(404, "记录不存在")
        await session.delete(record)
        await session.commit()
    return {"ok": True}
