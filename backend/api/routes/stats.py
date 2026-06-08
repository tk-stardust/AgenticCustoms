"""Dashboard 实时统计接口"""

from fastapi import APIRouter
from sqlalchemy import select, func

from data.db.database import async_session
from data.db.models import Declaration, HsCode

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_stats():
    """Dashboard 统计——全部从数据库实时计算"""
    async with async_session() as session:
        # 总申报次数
        total = (await session.execute(select(func.count(Declaration.id)))).scalar() or 0

        # 合规通过率（cross_check_passed = true 的比例）
        passed = (await session.execute(
            select(func.count(Declaration.id)).where(Declaration.results != None)
        )).scalar() or 0
        if passed > 0:
            ok = (await session.execute(
                select(func.count(Declaration.id)).where(
                    Declaration.results != None,
                    func.json_extract(Declaration.results, "$.cross_check_passed") == True,
                )
            )).scalar() or 0
            pass_rate = round(ok / passed * 100, 1) if passed > 0 else 100.0
        else:
            pass_rate = 100.0

        # 风险预警数（cross_check_passed = false）
        warnings = (await session.execute(
            select(func.count(Declaration.id)).where(
                Declaration.results != None,
                func.json_extract(Declaration.results, "$.cross_check_passed") == False,
            )
        )).scalar() or 0

        # HS 编码库总数
        hs_total = (await session.execute(select(func.count(HsCode.id)))).scalar() or 0

    return {
        "total": total,
        "pass_rate": pass_rate,
        "warnings": warnings,
        "hs_codes": hs_total,
    }
