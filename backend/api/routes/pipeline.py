"""一键全流程接口"""

import uuid

from fastapi import APIRouter

from domain.commodity import Commodity
from domain.declaration_doc import DeclarationDoc
from data.db.database import async_session
from data.db.models import Declaration
from orchestration.graph import run_pipeline
from shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["pipeline"])


@router.post("/pipeline/full", response_model=DeclarationDoc)
async def full_pipeline(commodity: Commodity, target_country: str = "US"):
    """一键全流程——HS归类 → 关税/合规/原产地(并行) → 申报文件

    :param commodity: 商品实体
    :param target_country: 目标国家代码，默认 US
    """
    rid = uuid.uuid4().hex[:12]
    logger.info("api.pipeline.request", name=commodity.name, country=target_country)

    result = await run_pipeline(commodity, target_country)
    result.request_id = rid

    # 保存申报记录
    async with async_session() as session:
        declaration = Declaration(
            request_id=rid,
            commodity_name=commodity.name,
            commodity_description=commodity.description,
            hs_code=result.customs_declaration.get("hs_code", ""),
            target_country=target_country,
            results=result.model_dump(),
            status="completed",
        )
        session.add(declaration)
        await session.commit()

    return result
