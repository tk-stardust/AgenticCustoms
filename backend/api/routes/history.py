"""申报历史记录接口"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, delete, func

from api.deps import require_user
from data.db.database import async_session
from data.db.models import Declaration, User
from shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def list_history(
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    filter: str = "all",
    user: User = Depends(require_user),
):
    """查询申报记录（分页 + 筛选）"""
    async with async_session() as session:
        query = select(Declaration).where(Declaration.user_id == user.id)
        count_q = select(func.count(Declaration.id)).where(Declaration.user_id == user.id)

        # 筛选
        if search:
            kw = f"%{search}%"
            query = query.where(
                (Declaration.commodity_name.like(kw)) | (Declaration.hs_code.like(kw))
            )
            count_q = count_q.where(
                (Declaration.commodity_name.like(kw)) | (Declaration.hs_code.like(kw))
            )
        if filter == "completed":
            query = query.where(Declaration.status == "completed")
            count_q = count_q.where(Declaration.status == "completed")
        elif filter == "failed":
            query = query.where(Declaration.status == "failed")
            count_q = count_q.where(Declaration.status == "failed")
        elif filter == "risk":
            query = query.where(
                Declaration.results != None,
                func.json_extract(Declaration.results, "$.cross_check_passed") == False,
            )
            count_q = count_q.where(
                Declaration.results != None,
                func.json_extract(Declaration.results, "$.cross_check_passed") == False,
            )

        total = (await session.execute(count_q)).scalar() or 0
        offset = (page - 1) * page_size
        result = await session.execute(
            query.order_by(desc(Declaration.created_at)).offset(offset).limit(page_size)
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
async def delete_record(record_id: int, user: User = Depends(require_user)):
    """删除指定申报记录"""
    async with async_session() as session:
        result = await session.execute(
            select(Declaration).where(Declaration.id == record_id, Declaration.user_id == user.id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(404, "记录不存在")
        await session.delete(record)
        await session.commit()
    return {"ok": True}
