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

        # 合规通过率
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
            pass_rate = round(ok / passed * 100, 1)
        else:
            pass_rate = 100.0

        # 风险预警数
        warnings = (await session.execute(
            select(func.count(Declaration.id)).where(
                Declaration.results != None,
                func.json_extract(Declaration.results, "$.cross_check_passed") == False,
            )
        )).scalar() or 0

        # HS 编码库总数
        hs_total = (await session.execute(select(func.count(HsCode.id)))).scalar() or 0

        # 按目标国分布
        country_rows = (await session.execute(
            select(Declaration.target_country, func.count(Declaration.id))
            .group_by(Declaration.target_country)
        )).all()
        by_country = [{"country": r[0], "count": r[1]} for r in country_rows] if country_rows else []

        # 按风险等级分布（从 results JSON 中统计）
        risk_green = (await session.execute(
            select(func.count(Declaration.id)).where(
                Declaration.results != None,
                func.json_extract(Declaration.results, "$.cross_check_passed") == True,
            )
        )).scalar() or 0
        risk_red = warnings
        risk_yellow = passed - risk_green - risk_red
        by_risk = [
            {"risk": "green", "count": risk_green},
            {"risk": "yellow", "count": max(0, risk_yellow)},
            {"risk": "red", "count": risk_red},
        ]

    return {
        "total": total,
        "pass_rate": pass_rate,
        "warnings": warnings,
        "hs_codes": hs_total,
        "by_country": by_country,
        "by_risk": by_risk,
    }
