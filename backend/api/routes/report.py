"""申报报告下载接口"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from data.db.database import async_session
from data.db.models import Declaration
from shared.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["report"])

REPORT_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><title>申报报告 — {commodity}</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:-apple-system,'Microsoft YaHei',sans-serif;color:#1e293b;max-width:720px;margin:40px auto;padding:0 20px}}
  h1{{font-size:22px;margin-bottom:4px}}
  .meta{{color:#64748b;font-size:13px;margin-bottom:24px}}
  .card{{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin-bottom:12px}}
  .card h3{{font-size:14px;color:#334155;margin-bottom:8px;border-bottom:1px solid #f1f5f9;padding-bottom:6px}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  td{{padding:6px 8px;border-bottom:1px solid #f8fafc}}
  td:first-child{{color:#64748b;width:120px}}
  .hs{{font-family:'JetBrains Mono',monospace;font-size:20px;color:#0d9488;font-weight:700}}
  .risk-green{{color:#22c55e}} .risk-yellow{{color:#f59e0b}} .risk-red{{color:#ef4444}}
  .footer{{margin-top:24px;text-align:center;font-size:11px;color:#94a3b8}}
  @media print{{body{{margin:0}} .card{{break-inside:avoid}}}}
</style></head>
<body>
<h1>跨境合规贸易申报报告</h1>
<p class="meta">商品：{commodity} &nbsp;|&nbsp; 目标国：{country} &nbsp;|&nbsp; 生成时间：{time}</p>

<div class="card"><h3>HS 编码归类</h3>
<table><tr><td>HS 编码</td><td class="hs">{hs_code}</td></tr>
<tr><td>商品名称</td><td>{commodity}</td></tr>
<tr><td>品目描述</td><td>{hs_desc}</td></tr></table></div>

<div class="card"><h3>报关单草单</h3>
<table>{decl_rows}</table></div>

<div class="card"><h3>合规信息</h3>
<p style="font-size:13px;line-height:1.6">{compliance}</p></div>

<div class="card"><h3>校验结果</h3>
<p style="font-size:13px;color:{check_color}">{check_status}</p>
{check_errors}</div>

<p class="footer">© 2026 AgenticCustoms · 由 AI 多智能体协作生成 · 仅供参考</p>
</body></html>"""


@router.get("/pipeline/report/{request_id}", response_class=HTMLResponse)
async def download_report(request_id: str):
    """下载申报报告 HTML 文件（浏览器可直接打开或打印为 PDF）

    :param request_id: 申报请求 ID
    """
    async with async_session() as session:
        result = await session.execute(
            select(Declaration).where(Declaration.request_id == request_id)
        )
        decl = result.scalar_one_or_none()

    if not decl:
        raise HTTPException(404, f"未找到申报记录: {request_id}")

    r = decl.results or {}
    cd = r.get("customs_declaration", {})
    oc = r.get("origin_certificate") or {}

    decl_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in cd.items()
    )

    check_passed = r.get("cross_check_passed", False)
    check_errors = r.get("cross_check_errors", [])
    check_color = "#22c55e" if check_passed else "#f59e0b"
    check_status = "✅ 全部校验通过" if check_passed else "⚠️ 存在校验警告"

    errors_html = ""
    if check_errors:
        errors_html = "".join(
            f'<p style="font-size:12px;color:#f59e0b;margin-top:4px">⚠ {e}</p>'
            for e in check_errors
        )

    oc_rows = ""
    if oc:
        oc_rows = '<div class="card"><h3>原产地证书</h3><table>' + "".join(
            f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in oc.items()
        ) + "</table></div>"

    html = REPORT_TPL.format(
        commodity=decl.commodity_name,
        country=decl.target_country,
        time=decl.created_at.strftime("%Y-%m-%d %H:%M") if decl.created_at else "",
        hs_code=decl.hs_code or "—",
        hs_desc=r.get("hs_code_description", cd.get("hs_code", "")),
        decl_rows=decl_rows,
        compliance=r.get("compliance_statement", "—"),
        check_color=check_color,
        check_status=check_status,
        check_errors=errors_html,
    )
    html = html.replace("{oc_section}", oc_rows)

    return HTMLResponse(content=html, headers={
        "Content-Disposition": f"attachment; filename=report_{request_id}.html"
    })
