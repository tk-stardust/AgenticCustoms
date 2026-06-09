"""申报历史记录接口"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, desc, delete, func

from data.db.database import async_session
from data.db.models import Declaration
from shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def list_history(page: int = 1, page_size: int = 20):
    """查询申报记录（分页）

    :param page: 页码，从 1 开始
    :param page_size: 每页条数，默认 20
    """
    async with async_session() as session:
        # 总数
        total = (await session.execute(select(func.count(Declaration.id)))).scalar() or 0

        # 分页数据
        offset = (page - 1) * page_size
        result = await session.execute(
            select(Declaration)
            .order_by(desc(Declaration.created_at))
            .offset(offset)
            .limit(page_size)
        )
        rows = result.scalars().all()
        items = [
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

    return {"items": items, "total": total, "page": page, "page_size": page_size}


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
