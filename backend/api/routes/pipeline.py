"""一键全流程接口"""

import io
import uuid
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import select

from domain.commodity import Commodity
from domain.declaration_doc import DeclarationDoc
from api.deps import require_user
from data.db.database import async_session
from data.db.models import Declaration, User
from orchestration.graph import run_pipeline, run_pipeline_stream
from shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["pipeline"])


A4_TPL = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title>
<style>
  body{{font-family:'SimSun','宋体','PingFang SC',sans-serif;font-size:13px;line-height:1.8;max-width:800px;margin:0 auto;padding:40px 56px;color:#1e293b}}
  h2{{text-align:center;font-size:18px;font-weight:700;margin-bottom:20px;letter-spacing:2px}}
  table{{width:100%;border-collapse:collapse;margin:16px 0;border:1px solid #333}}
  th,td{{padding:8px 10px;border:1px solid #333;font-size:13px}}
  th{{background:#f8fafc;text-align:left;font-size:12px;color:#666}}
  .section{{margin-bottom:20px}} .section h3{{font-size:14px;font-weight:600;margin-bottom:8px}}
  .footer{{text-align:center;color:#999;font-size:12px;margin-top:24px}}
  .badge-red{{color:#ef4444;font-weight:700}} .badge-yellow{{color:#f59e0b;font-weight:700}} .badge-green{{color:#10b981;font-weight:700}}
</style></head><body>
{body}
</body></html>"""


def _build_customs_html(doc: dict) -> str:
    d = doc.get("customs_declaration", {})
    items = d.get("tariff_items", [])
    rows = "".join(
        f"<tr><td>{i.get('name','')}</td><td>{i.get('rate',0)}%</td><td>{i.get('amount','—')}</td><td>{i.get('note','')}</td></tr>"
        for i in items
    )
    body = f"""<h2>中华人民共和国海关出口货物报关单</h2>
<p>预录入编号：{doc.get('request_id','')} &nbsp;|&nbsp; 申报日期：待填写</p>
<div class="section"><h3>基本信息</h3>
  <p>商品名称：<b>{d.get('commodity_name','')}</b> | HS编码：{d.get('hs_code','')} | 原产地：{d.get('origin','CN')}</p>
  <p>数量：{d.get('quantity','')} 件 | 申报价值：{d.get('declared_value','')} 元 | 目标国：待填写</p>
</div>
<div class="section"><h3>税费明细</h3>
  <table><tr><th>税项</th><th>税率</th><th>金额（元）</th><th>备注</th></tr>{rows}</table>
  <p>综合税率：<b>{d.get('total_tax_rate','')}%</b> | FTA：{d.get('fta_applied') or '无'} | 节省：{d.get('fta_saving','—')} 元</p>
</div>
<p class="footer">AgenticCustoms 智能合规平台 &copy; 2026</p>"""
    return A4_TPL.format(title="报关单草单", body=body)


def _build_origin_html(doc: dict) -> str:
    o = doc.get("origin_certificate") or {}
    body = f"""<h2>原产地证书申请书</h2>
<div class="section">
  <p><b>HS编码：</b>{o.get('hs_code','')} | <b>出口国：</b>{o.get('origin_country','CN')} | <b>进口国：</b>{o.get('destination_country','')}</p>
  <p><b>适用FTA：</b>{o.get('fta','不适用')} | <b>原产地标准：</b>{o.get('origin_criteria','—')}</p>
  <p><b>区域价值成分 RVC：</b>{o.get('rvc_percentage','—')}% | <b>备注：</b>{o.get('note','')}</p>
</div>
<p class="footer">申请人签章：________ &nbsp;&nbsp; 日期：________</p>"""
    return A4_TPL.format(title="原产地证书申请书", body=body)


def _build_compliance_html(doc: dict) -> str:
    cs = doc.get("compliance_statement", "")
    cross = "全部通过" if doc.get("cross_check_passed") else "存在矛盾项：" + ", ".join(doc.get("cross_check_errors", []))
    body = f"""<h2>跨境贸易合规声明</h2>
<div class="section">
  <p><b>声明编号：</b>CC-{doc.get('request_id','')} | <b>生成日期：</b>待填写</p>
</div>
<div class="section"><h3>合规声明</h3><p>{cs}</p></div>
<div class="section"><h3>交叉校验</h3><p>{cross}</p></div>
<p class="footer">本声明自生成之日起30日内有效 | AgenticCustoms 智能合规平台 &copy; 2026</p>"""
    return A4_TPL.format(title="合规声明", body=body)


@router.get("/pipeline/download/{request_id}")
async def download_zip(request_id: str):
    """下载申报文件 ZIP（报关单 + 原产地证 + 合规声明 三份 HTML）"""
    async with async_session() as session:
        result = await session.execute(
            select(Declaration).where(Declaration.request_id == request_id)
        )
        row = result.scalar_one_or_none()
        if not row or not row.results:
            raise HTTPException(404, "记录不存在或无结果数据")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("报关单草单.html", _build_customs_html(row.results))
        zf.writestr("原产地证书申请书.html", _build_origin_html(row.results))
        zf.writestr("合规声明.html", _build_compliance_html(row.results))

    buf.seek(0)
    filename = f"AgenticCustoms_{request_id}.zip"
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/pipeline/full")
async def full_pipeline(commodity: Commodity, target_country: str = "US", user=Depends(require_user)):
    """一键全流程——HS归类 → 关税/合规/原产地(并行) → 申报文件"""
    rid = uuid.uuid4().hex[:12]
    logger.info("api.pipeline.request", name=commodity.name, country=target_country)

    state = await run_pipeline(commodity, target_country)
    doc: DeclarationDoc = state["documents"]
    doc.request_id = rid

    async with async_session() as session:
        declaration = Declaration(
            request_id=rid,
            user_id=user.id,
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
async def pipeline_stream(commodity: Commodity, target_country: str = "US", user: User = Depends(require_user)):
    """SSE 流式全流程——每个 Agent 完成时推送进度事件"""
    rid = uuid.uuid4().hex[:12]
    logger.info("api.pipeline.stream", name=commodity.name, country=target_country)

    results_holder: dict = {}

    async def generate():
        async for chunk in run_pipeline_stream(commodity, target_country):
            if chunk.startswith("event: done"):
                import json as _json
                data_str = chunk.split("data: ", 1)[1].strip()
                event_data = _json.loads(data_str)
                results_holder["data"] = event_data
                doc = DeclarationDoc(**event_data["documents"])
                doc.request_id = rid
                async with async_session() as session:
                    declaration = Declaration(
                        request_id=rid,
                        user_id=user.id,
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
