"""申报历史记录接口"""

from fastapi import APIRouter
from sqlalchemy import select, desc

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
                "hs_code": r.hs_code,
                "target_country": r.target_country,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "results": r.results,
            }
            for r in rows
        ]
