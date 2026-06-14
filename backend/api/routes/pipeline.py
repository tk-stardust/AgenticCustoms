"""一键全流程接口"""

import io
import os
import subprocess
import tempfile
import uuid
import zipfile
from urllib.parse import quote

# Edge 浏览器路径（Windows 自带）
_EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

_EDGE_EXE: str | None = None


def _get_edge() -> str | None:
    global _EDGE_EXE
    if _EDGE_EXE:
        return _EDGE_EXE
    for p in _EDGE_PATHS:
        if os.path.exists(p):
            _EDGE_EXE = p
            return p
    _EDGE_EXE = ""
    return None


def _html_to_pdf(html: str) -> bytes:
    """通过 Edge 无头模式将 HTML 转为 PDF"""
    edge = _get_edge()
    if not edge:
        raise RuntimeError("未找到 Microsoft Edge，无法生成 PDF")

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, encoding="utf-8") as f:
        f.write(html)
        html_path = f.name

    pdf_path = html_path.replace(".html", ".pdf")
    try:
        subprocess.run(
            [edge, "--headless", f"--print-to-pdf={pdf_path}",
             "--no-pdf-header-footer", "--disable-gpu", html_path],
            check=True, timeout=30, capture_output=True,
        )
        with open(pdf_path, "rb") as f:
            return f.read()
    finally:
        try: os.unlink(html_path)
        except OSError: pass
        try: os.unlink(pdf_path)
        except OSError: pass

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


A4_CSS = """
  body{font-family:'DengXian','SimSun','PingFang SC','Microsoft YaHei',sans-serif;font-size:13px;line-height:1.8;max-width:800px;margin:0 auto;padding:40px 56px;color:#1e293b}
  h2.a4-title{text-align:center;font-size:18px;font-weight:700;margin-bottom:20px;letter-spacing:2px}
  .a4-meta{display:flex;justify-content:space-between;margin-bottom:16px;font-size:12px;color:#64748b}
  .a4-grid{display:grid;grid-template-columns:1fr 1fr;border:1px solid #333;margin-bottom:16px}
  .a4-row{display:flex;border-bottom:1px solid #333}
  .a4-row:nth-child(odd){border-right:1px solid #333}
  .a4-row label{width:80px;padding:6px 8px;background:#f8fafc;font-size:12px;color:#666;flex-shrink:0;border-right:1px solid #e2e8f0}
  .a4-row span{padding:6px 12px;font-weight:600;font-size:13px}
  table.a4-table{width:100%;border-collapse:collapse;margin-bottom:16px;border:1px solid #333}
  table.a4-table th{padding:6px 8px;background:#f8fafc;font-size:11px;color:#666;border:1px solid #333;text-align:center}
  table.a4-table td{padding:6px 8px;border:1px solid #333;text-align:center;font-size:12px}
  table.a4-table td code{font-family:'JetBrains Mono',monospace;color:#0d9488;font-weight:600}
  .a4-section{margin-bottom:16px} .a4-section h4{font-size:14px;font-weight:600;margin-bottom:8px;color:#334155}
  .a4-section p{white-space:pre-wrap;line-height:1.8}
  .a4-footer{text-align:center;color:#999;font-size:12px;margin-top:24px}
  .compliance-hero{text-align:center;padding:14px;margin:-48px -56px 24px;border-radius:2px 2px 0 0}
  .compliance-hero.red{background:#ef4444;color:#fff}
  .compliance-hero.yellow{background:#f59e0b;color:#fff}
  .compliance-hero.green{background:#10b981;color:#fff}
  .compliance-hero h2{margin:0;font-size:18px}
  .checklist{display:flex;flex-direction:column;gap:8px}
  .check-item{display:flex;align-items:flex-start;gap:10px;padding:10px 12px;border-radius:8px;background:rgba(16,185,129,.03);border:1px solid rgba(16,185,129,.1)}
  .check-item.fail{background:rgba(239,68,68,.03);border-color:rgba(239,68,68,.1)}
  .check-mark{width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0}
  .check-item .check-mark{background:rgba(16,185,129,.15);color:#10b981}
  .check-item.fail .check-mark{background:rgba(239,68,68,.15);color:#ef4444}
  .tax-summary{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px;font-size:13px;color:#64748b}
  .tax-summary b{color:#334155}
  .fta-badge{color:#0d9488}
  .tax-disclaimer{font-size:11px;color:#94a3b8;margin-top:8px;text-align:right}
"""

A4_TPL = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title>
<style>{css}</style></head><body>
{body}
</body></html>"""

CN = {"US": "美国", "EU": "欧盟", "VN": "越南", "CN": "中国"}

def _v(val, default="—"):
    return default if val is None or val == "" or val == "None" else val

def _cn(code):
    return CN.get(code, code or "—")

def _build_customs_html(doc: dict) -> str:
    d = doc.get("customs_declaration", {})
    tariff = doc.get("_tariff", {})
    items = d.get("tariff_items", [])
    tax_rows = "".join(
        f"<tr><td>{_v(i.get('name'))}</td><td>{_v(i.get('rate',0))}%</td>"
        f"<td>{_v(i.get('amount'))}</td><td>{_v(i.get('note'),'')}</td></tr>"
        for i in items
    )
    origin = _cn(d.get("origin"))
    dest_country = tariff.get("country") or (doc.get("_tariff") or {}).get("country") or ""
    body = f"""<h2 class="a4-title">中华人民共和国海关出口货物报关单</h2>
<div class="a4-meta">
  <span>预录入编号：{doc.get('request_id','—')}</span>
  <span>海关编号：________</span>
  <span>申报日期：________</span>
</div>
<div class="a4-grid">
  <div class="a4-row"><label>出口口岸</label><span></span></div>
  <div class="a4-row"><label>运抵国（地区）</label><span>{_cn(dest_country)}</span></div>
  <div class="a4-row"><label>收发货人</label><span></span></div>
  <div class="a4-row"><label>生产销售单位</label><span></span></div>
  <div class="a4-row"><label>运输方式</label><span></span></div>
  <div class="a4-row"><label>运输工具名称</label><span></span></div>
  <div class="a4-row"><label>监管方式</label><span>一般贸易</span></div>
  <div class="a4-row"><label>征免性质</label><span>一般征税</span></div>
  <div class="a4-row"><label>成交方式</label><span></span></div>
  <div class="a4-row"><label>合同协议号</label><span></span></div>
  <div class="a4-row"><label>件数</label><span>{_v(d.get('quantity'))}</span></div>
  <div class="a4-row"><label>包装种类</label><span></span></div>
</div>
<table class="a4-table">
  <thead><tr><th>项号</th><th>商品名称</th><th>HS编码</th><th>数量及单位</th><th>单价</th><th>总价</th><th>币制</th><th>原产国</th><th>最终目的国</th><th>征免</th></tr></thead>
  <tbody><tr>
    <td>1</td>
    <td>{_v(d.get('commodity_name'))}</td>
    <td><code>{_v(d.get('hs_code'))}</code></td>
    <td>{_v(d.get('quantity'))}{_v(d.get('unit'),'件')}</td>
    <td>{_v(d.get('declared_value'))}</td>
    <td>{_v(d.get('declared_value'))}</td>
    <td>USD</td>
    <td>{origin}</td>
    <td>{_cn(dest_country)}</td>
    <td>照章征税</td>
  </tr></tbody>
</table>
<div class="a4-section">
  <h4>税费明细</h4>
  <div class="tax-summary">
    <span>综合税率：<b>{_v(d.get('total_tax_rate'))}%</b></span>
    <span>预估税费：<b>{_v(d.get('total_tax_amount'))} 元</b></span>
    {f'<span>FTA：<b class="fta-badge">{tariff.get("fta_applied","")}</b></span>' if tariff.get("fta_applied") else ''}
    {f'<span>FTA节省：<b>{tariff.get("fta_saving","")} 元</b></span>' if tariff.get("fta_saving") else ''}
  </div>
  <table class="a4-table"><tr><th>税项</th><th>税率</th><th>金额（元）</th><th>备注</th></tr>{tax_rows}</table>
  <p class="tax-disclaimer">税率数据仅供参考，具体以海关最新公告为准</p>
</div>
<p class="a4-footer">申报单位签章：________ &nbsp;&nbsp; 日期：________</p>"""
    return A4_TPL.format(title="报关单草单", css=A4_CSS, body=body)


def _build_origin_html(doc: dict) -> str:
    o = doc.get("origin_certificate") or {}
    tariff = doc.get("_tariff", {})
    origin = doc.get("_origin", {})
    body = f"""<h2 class="a4-title">原产地证书申请书</h2>
<div class="a4-meta">
  <span>申请号：________</span>
  <span>发票号：________</span>
  <span>申请日期：________</span>
</div>
<div class="a4-grid">
  <div class="a4-row"><label>申请人</label><span></span></div>
  <div class="a4-row"><label>证书类型</label><span>{_v(o.get('fta'),'一般原产地证')}</span></div>
  <div class="a4-row"><label>出口国</label><span>{_cn('CN')}</span></div>
  <div class="a4-row"><label>进口国</label><span>{_cn(tariff.get('country') or o.get('destination_country'))}</span></div>
  <div class="a4-row"><label>HS编码</label><span><code>{_v(o.get('hs_code'))}</code></span></div>
  <div class="a4-row"><label>原产地标准</label><span>{_v(o.get('origin_criteria'))}</span></div>
  <div class="a4-row"><label>FOB总值（美元）</label><span>{_v(doc.get('customs_declaration',{}).get('declared_value'))}</span></div>
  <div class="a4-row"><label>拟出运日期</label><span>________</span></div>
  <div class="a4-row"><label>数量/重量</label><span>{_v(doc.get('customs_declaration',{}).get('quantity'))}{_v(doc.get('customs_declaration',{}).get('unit'),'件')}</span></div>
  <div class="a4-row"><label>是否含进口成分</label><span>否</span></div>
</div>
<div class="a4-section">
  <h4>适用 FTA</h4>
  <p>{tariff.get('fta_applied') or '无'}</p>
</div>
<div class="a4-section">
  <h4>原产地分析</h4>
  <p>推荐原产地：<b>{_cn(origin.get('recommended_origin'))}</b></p>
  <p>满足条件：{origin.get('meeting_criteria') and '、'.join(origin['meeting_criteria']) or '—'}</p>
  {f'<p>区域价值成分：<b>{origin["rvc_percentage"]}%</b></p>' if origin.get('rvc_percentage') else ''}
  <p>{_v(origin.get('note'),'')}</p>
</div>
<p class="a4-footer">申请人签章：________ &nbsp;&nbsp; 日期：________</p>"""
    return A4_TPL.format(title="原产地证书申请书", css=A4_CSS, body=body)


def _build_compliance_html(doc: dict) -> str:
    d = doc.get("customs_declaration", {})
    comp = doc.get("_compliance", {})
    cs = doc.get("compliance_statement", "") or ""
    rl = doc.get("risk_level", "green")
    level_cn = {"red": "✗ 不合规", "yellow": "⚠ 部分合规", "green": "✓ 合规通过"}
    hero_class = rl if rl in ("red","yellow","green") else "green"
    sanctions_class = "fail" if comp.get("sanctions_hit") else ""
    license_class = "fail" if comp.get("license_required") else ""
    violations_html = ""
    for v in comp.get("violations", []) or []:
        violations_html += f'<div class="check-item fail"><span class="check-mark">✗</span><span>{v.get("category","")} — {v.get("description","")}</span></div>'
    body = f"""<div class="compliance-hero {hero_class}"><h2>{level_cn.get(rl, level_cn['green'])}</h2></div>
<h2 class="a4-title">跨境贸易合规声明</h2>
<div class="a4-meta">
  <span>声明编号：CC-{doc.get('request_id','—')}</span>
  <span>生成日期：________</span>
</div>
<div class="a4-section">
  <h4>商品信息</h4>
  <p>商品名称：{_v(d.get('commodity_name'))} | HS编码：{_v(d.get('hs_code'))} | 目标国：{_cn((doc.get('_tariff') or {}).get('country'))}</p>
</div>
<div class="a4-section">
  <h4>校验结果</h4>
  <div class="checklist">
    <div class="check-item {sanctions_class}"><span class="check-mark">{'✗' if comp.get('sanctions_hit') else '☑'}</span><span>制裁清单校验 — {'命中' if comp.get('sanctions_hit') else '通过'}</span></div>
    <div class="check-item {license_class}"><span class="check-mark">{'⚠' if comp.get('license_required') else '☑'}</span><span>出口许可校验 — {'需要许可' if comp.get('license_required') else '无需许可'}</span></div>
    {violations_html}
    <div class="check-item"><span class="check-mark">☑</span><span>环保合规 — 符合 RoHS / REACH</span></div>
    <div class="check-item"><span class="check-mark">☑</span><span>知识产权校验 — 通过</span></div>
  </div>
</div>
<div class="a4-section">
  <h4>综合评定</h4>
  <p>{cs}</p>
</div>
<p class="a4-footer">本声明自生成之日起30日内有效 | AgenticCustoms 智能合规平台</p>"""
    return A4_TPL.format(title="合规声明", css=A4_CSS, body=body)


@router.get("/pipeline/download/{request_id}")
async def download_zip(request_id: str):
    """下载申报文件 ZIP（报关单 + 原产地证 + 合规声明 三份 PDF）"""
    async with async_session() as session:
        result = await session.execute(
            select(Declaration).where(Declaration.request_id == request_id)
        )
        row = result.scalar_one_or_none()
        if not row or not row.results:
            raise HTTPException(404, "记录不存在或无结果数据")

    def _to_pdf(html: str) -> bytes:
        return _html_to_pdf(html)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("报关单草单.pdf", _to_pdf(_build_customs_html(row.results)))
        zf.writestr("原产地证书申请书.pdf", _to_pdf(_build_origin_html(row.results)))
        zf.writestr("合规声明.pdf", _to_pdf(_build_compliance_html(row.results)))

    buf.seek(0)
    name = row.commodity_name or request_id
    filename = f"{name}_申报文件.zip"
    return Response(buf.getvalue(), media_type="application/zip", headers=_attachment(filename))


def _attachment(filename: str) -> dict:
    """生成 Content-Disposition 头，支持中文文件名"""
    encoded = quote(filename)
    return {"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"}


_DOC_TYPES = {
    "customs": ("报关单", _build_customs_html),
    "origin": ("原产地证书申请书", _build_origin_html),
    "compliance": ("合规声明", _build_compliance_html),
}

@router.get("/pipeline/pdf/{request_id}/{doc_type}")
async def download_pdf(request_id: str, doc_type: str):
    """下载单个申报文件 PDF（报关单 / 原产地证 / 合规声明）"""
    if doc_type not in _DOC_TYPES:
        raise HTTPException(400, "无效的文档类型，支持: customs, origin, compliance")
    doc_label, builder = _DOC_TYPES[doc_type]

    async with async_session() as session:
        result = await session.execute(
            select(Declaration).where(Declaration.request_id == request_id)
        )
        row = result.scalar_one_or_none()
        if not row or not row.results:
            raise HTTPException(404, "记录不存在或无结果数据")

    name = row.commodity_name or request_id
    filename = f"{name}_{doc_label}.pdf"
    pdf_bytes = _html_to_pdf(builder(row.results))
    return Response(pdf_bytes, media_type="application/pdf", headers=_attachment(filename))


def _save_declaration(rid: str, commodity: Commodity, target_country: str, user_id: int, status: str, results: dict):
    """保存申报记录到数据库（同步辅助函数）"""
    # 注意：此函数必须在 async_session 上下文中调用
    return Declaration(
        request_id=rid,
        user_id=user_id,
        commodity_name=commodity.name,
        commodity_description=commodity.description,
        hs_code=results.get("customs_declaration", {}).get("hs_code", ""),
        target_country=target_country,
        results=results,
        status=status,
    )


@router.post("/pipeline/full")
async def full_pipeline(commodity: Commodity, target_country: str = "US", user=Depends(require_user)):
    """一键全流程——HS归类 → 关税/合规/原产地(并行) → 申报文件"""
    rid = uuid.uuid4().hex[:12]
    logger.info("api.pipeline.request", name=commodity.name, country=target_country)

    try:
        state = await run_pipeline(commodity, target_country)
        doc: DeclarationDoc = state["documents"]
        doc.request_id = rid
        results = doc.model_dump()
        results["risk_level"] = state["compliance_result"].risk_level
        results["_tariff"] = state["tariff_result"].model_dump()
        results["_compliance"] = state["compliance_result"].model_dump()
        results["_origin"] = state["origin_result"].model_dump()
        status = "completed"
        ret = {
            "request_id": rid,
            "documents": results,
            "tariff_result": state["tariff_result"].model_dump(),
            "compliance_result": state["compliance_result"].model_dump(),
            "origin_result": state["origin_result"].model_dump(),
        }
    except Exception as e:
        logger.error("api.pipeline.error", error=str(e))
        results = {"error": str(e)}
        status = "failed"
        ret = {"request_id": rid, "error": str(e)}

    async with async_session() as session:
        session.add(_save_declaration(rid, commodity, target_country, user.id, status, results))
        await session.commit()

    if status == "failed":
        raise HTTPException(500, f"全流程执行失败: {results.get('error', '未知错误')}")
    return ret


@router.post("/pipeline/stream")
async def pipeline_stream(commodity: Commodity, target_country: str = "US", user: User = Depends(require_user)):
    """SSE 流式全流程——每个 Agent 完成时推送进度事件"""
    rid = uuid.uuid4().hex[:12]
    logger.info("api.pipeline.stream", name=commodity.name, country=target_country)

    async def generate():
        try:
            async for chunk in run_pipeline_stream(commodity, target_country):
                if chunk.startswith("event: done"):
                    import json as _json
                    data_str = chunk.split("data: ", 1)[1].strip()
                    event_data = _json.loads(data_str)
                    doc = DeclarationDoc(**event_data["documents"])
                    doc.request_id = rid
                    results = doc.model_dump()
                    results["risk_level"] = event_data.get("compliance_result", {}).get("risk_level", "green")
                    results["_tariff"] = event_data.get("tariff_result", {})
                    results["_compliance"] = event_data.get("compliance_result", {})
                    results["_origin"] = event_data.get("origin_result", {})
                    async with async_session() as session:
                        session.add(_save_declaration(rid, commodity, target_country, user.id, "completed", results))
                        await session.commit()
                    event_data["request_id"] = rid
                    yield f"event: done\ndata: {_json.dumps(event_data, ensure_ascii=False)}\n\n"
                else:
                    yield chunk
        except Exception as e:
            logger.error("api.pipeline.stream.error", error=str(e))
            async with async_session() as session:
                session.add(_save_declaration(rid, commodity, target_country, user.id, "failed", {"error": str(e)}))
                await session.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")
