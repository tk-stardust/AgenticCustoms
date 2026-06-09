"""一键全流程接口"""

import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from domain.commodity import Commodity
from domain.declaration_doc import DeclarationDoc
from data.db.database import async_session
from data.db.models import Declaration
from orchestration.graph import run_pipeline, run_pipeline_stream
from shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["pipeline"])


@router.post("/pipeline/full")
async def full_pipeline(commodity: Commodity, target_country: str = "US"):
    """一键全流程——HS归类 → 关税/合规/原产地(并行) → 申报文件

    返回包含所有中间结果和最终 DeclarationDoc 的完整响应。
    """
    rid = uuid.uuid4().hex[:12]
    logger.info("api.pipeline.request", name=commodity.name, country=target_country)

    state = await run_pipeline(commodity, target_country)
    doc: DeclarationDoc = state["documents"]
    doc.request_id = rid

    # 保存申报记录
    async with async_session() as session:
        declaration = Declaration(
            request_id=rid,
            commodity_name=commodity.name,
            commodity_description=commodity.description,
            hs_code=doc.customs_declaration.get("hs_code", ""),
            target_country=target_country,
            results=doc.model_dump(),
            status="completed",
        )
        session.add(declaration)
        await session.commit()

    return {
        "request_id": rid,
        "documents": doc.model_dump(),
        "tariff_result": state["tariff_result"].model_dump(),
        "compliance_result": state["compliance_result"].model_dump(),
        "origin_result": state["origin_result"].model_dump(),
    }


@router.post("/pipeline/stream")
async def pipeline_stream(commodity: Commodity, target_country: str = "US"):
    """SSE 流式全流程——每个 Agent 完成时推送进度事件，替代前端假动画"""
    rid = uuid.uuid4().hex[:12]
    logger.info("api.pipeline.stream", name=commodity.name, country=target_country)

    results_holder: dict = {}

    async def generate():
        async for chunk in run_pipeline_stream(commodity, target_country):
            # 拦截 done 事件，保存记录
            if chunk.startswith("event: done"):
                import json as _json
                data_str = chunk.split("data: ", 1)[1].strip()
                event_data = _json.loads(data_str)
                results_holder["data"] = event_data
                # 保存申报记录
                doc = DeclarationDoc(**event_data["documents"])
                doc.request_id = rid
                async with async_session() as session:
                    declaration = Declaration(
                        request_id=rid,
                        commodity_name=commodity.name,
                        commodity_description=commodity.description,
                        hs_code=doc.customs_declaration.get("hs_code", ""),
                        target_country=target_country,
                        results=doc.model_dump(),
                        status="completed",
                    )
                    session.add(declaration)
                    await session.commit()
                # 注入 request_id
                event_data["request_id"] = rid
                yield f"event: done\ndata: {_json.dumps(event_data, ensure_ascii=False)}\n\n"
            else:
                yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")
