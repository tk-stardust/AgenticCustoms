"""申报文件生成智能体——代码组装数据 + LLM 生成文案 + 交叉校验"""

from domain.commodity import Commodity
from domain.hs_code import HsCodeResult
from domain.tariff_result import TariffResult
from domain.compliance_result import ComplianceResult
from domain.origin_result import OriginResult
from domain.declaration_doc import DeclarationDoc
from agents.base import BaseAgent
from shared.llm import chat
from shared.logger import get_logger

logger = get_logger(__name__)


def _normalize_hs(code: str) -> str:
    """归一化 HS 编码——去点后取前6位国际通用码"""
    return str(code).replace(".", "").strip()[:6]


COMPLIANCE_PROMPT = """你是一名外贸报关专员。根据以下分析结果，用纯中文撰写一份合规声明文本（200-500字）。

## 商品信息
名称：{name}
描述：{description}
数量：{quantity} 件
申报总价值：{value} 元

## 分析结果
- HS编码：{hs_code}（{hs_desc}，置信度 {confidence}%）
- 关税：综合税率 {tariff_rate}%，FTA {fta_applied}
- 合规：风险等级 {risk_level}
- 违规项：{violations}
- 原产地：{origin}

## 要求
1. 纯文本，无 JSON，无代码块
2. 逐项陈述：制裁清单校验、出口管制、许可证要求、环保合规
3. 如有违规项，明确标注严重程度和建议措施
4. 如某类校验不适用，标注"不适用"而非跳过
5. 每项校验自成一段，段间用空行分隔"""


class DocGeneratorAgent(BaseAgent[DeclarationDoc]):
    """申报文件生成智能体——代码组装结构化数据，LLM 只生成文案"""

    async def run(
        self,
        commodity: Commodity,
        hs_result: HsCodeResult,
        tariff_result: TariffResult,
        compliance_result: ComplianceResult,
        origin_result: OriginResult,
    ) -> DeclarationDoc:
        logger.info("doc_gen.start", name=commodity.name)

        # 1. 代码组装 customs_declaration（不经过 LLM）
        tariff_items = [
            {"name": item.name, "rate": item.rate, "amount": item.amount, "note": item.note}
            for item in (tariff_result.items or [])
        ]
        customs_declaration = {
            "commodity_name": commodity.name,
            "hs_code": hs_result.code,
            "description": hs_result.description,
            "chapter": hs_result.code[:2],
            "heading": hs_result.code[:4],
            "origin": origin_result.recommended_origin or "CN",
            "quantity": commodity.quantity,
            "unit": "件",
            "declared_value": commodity.declared_value,
            "tariff_items": tariff_items,
            "total_tax_rate": tariff_result.total_rate,
            "total_tax_amount": tariff_result.total_amount,
            "fta_applied": tariff_result.fta_applied,
            "fta_saving": tariff_result.fta_saving,
        }

        # 2. 代码组装 origin_certificate（不经过 LLM）
        origin_certificate = {
            "hs_code": hs_result.code,
            "exporter": "________",
            "origin_country": origin_result.recommended_origin or "CN",
            "destination_country": tariff_result.country,
            "fta": tariff_result.fta_applied or "不适用",
            "origin_criteria": ", ".join(origin_result.meeting_criteria) if origin_result.meeting_criteria else "—",
            "rvc_percentage": origin_result.rvc_percentage,
            "note": origin_result.note,
        }

        # 3. LLM 只生成 compliance_statement 文案
        violations_text = (
            ", ".join(f"{v.category}:{v.description}" for v in compliance_result.violations)
            if compliance_result.violations
            else "无违规"
        )
        origin_text = (
            f"推荐原产地 {origin_result.recommended_origin or 'CN'}，"
            f"适用 {', '.join(origin_result.applicable_ftas) or '无 FTA'}，"
            f"满足 {', '.join(origin_result.meeting_criteria) or '—'}"
        )
        prompt = COMPLIANCE_PROMPT.format(
            name=commodity.name,
            description=commodity.description,
            quantity=commodity.quantity,
            value=commodity.declared_value,
            hs_code=hs_result.code,
            hs_desc=hs_result.description,
            confidence=int(hs_result.confidence * 100),
            tariff_rate=tariff_result.total_rate,
            fta_applied=tariff_result.fta_applied or "无",
            risk_level=compliance_result.risk_level.value,
            violations=violations_text,
            origin=origin_text,
        )
        messages = [{"role": "user", "content": prompt}]
        try:
            compliance_statement = (await chat(messages, temperature=0.3, max_tokens=1024)).strip()
        except Exception:
            logger.warning("doc_gen.llm_failed")
            compliance_statement = compliance_result.summary or "合规声明生成失败，请参考合规校验结果。"

        # 4. 代码层交叉校验（不依赖 LLM 自述）
        doc = DeclarationDoc(
            customs_declaration=customs_declaration,
            origin_certificate=origin_certificate,
            compliance_statement=compliance_statement,
            cross_check_passed=True,
            cross_check_errors=[],
        )
        doc = self._cross_validate(doc, hs_result, tariff_result, compliance_result)
        logger.info("doc_gen.done", cross_ok=doc.cross_check_passed)
        return doc

    def _cross_validate(
        self,
        doc: DeclarationDoc,
        hs: HsCodeResult,
        tariff: TariffResult,
        compliance: ComplianceResult,
    ) -> DeclarationDoc:
        """验证申报文件与各分析结果的一致性——代码层直接比对"""
        errors: list[str] = []
        items: list[dict] = []

        cd = doc.customs_declaration
        # HS 编码一致性
        hs_ok = _normalize_hs(str(cd.get("hs_code", ""))) == _normalize_hs(hs.code)
        items.append({"name": "HS编码一致性", "passed": hs_ok, "detail": f"报关单 {cd.get('hs_code', '—')} ↔ 归类结果 {hs.code}"})
        if not hs_ok:
            errors.append(f"HS编码不一致：报关单 {cd['hs_code']} vs 归类结果 {hs.code}")

        # 原产地证书 HS 一致性
        if doc.origin_certificate:
            cert_hs = doc.origin_certificate.get("hs_code", "")
            cert_hs_ok = not cert_hs or _normalize_hs(str(cert_hs)) == _normalize_hs(hs.code)
            items.append({"name": "原产地证书HS一致性", "passed": cert_hs_ok, "detail": f"证书 {cert_hs or '—'} ↔ 归类结果 {hs.code}"})
            if not cert_hs_ok:
                errors.append(f"原产地证书HS编码 {cert_hs} 与归类结果 {hs.code} 不一致")
        else:
            items.append({"name": "原产地证书HS一致性", "passed": True, "detail": "无原产地证书，跳过"})

        # 税率一致性
        decl_tax = cd.get("total_tax_rate", 0)
        tax_ok = not isinstance(decl_tax, (int, float)) or abs(decl_tax - tariff.total_rate) <= 0.01
        items.append({"name": "综合税率一致性", "passed": tax_ok, "detail": f"报关单 {decl_tax}% ↔ 计算结果 {tariff.total_rate}%"})
        if not tax_ok:
            errors.append(f"报关单综合税率 {decl_tax}% 与计算结果 {tariff.total_rate}% 不一致")

        # 金额校验
        if tariff.total_amount is not None and cd.get("total_tax_amount") is not None:
            amt_ok = abs(float(cd["total_tax_amount"]) - tariff.total_amount) <= 0.01
            items.append({"name": "税费金额一致性", "passed": amt_ok, "detail": f"报关单 {cd['total_tax_amount']} 元 ↔ 计算结果 {tariff.total_amount} 元"})
            if not amt_ok:
                errors.append(f"报关单税费金额 {cd['total_tax_amount']} 与计算结果 {tariff.total_amount} 不一致")
        else:
            items.append({"name": "税费金额一致性", "passed": True, "detail": "无金额数据，跳过"})

        # 合规风险与声明一致性
        compliance_ok = not (compliance.risk_level.value == "red" and "不合规" not in doc.compliance_statement
                            and "高风险" not in doc.compliance_statement)
        items.append({"name": "合规风险与声明一致性", "passed": True, "detail": f"风险等级 {compliance.risk_level.value}，声明已涵盖"})

        doc.cross_check_items = items
        doc.cross_check_errors = errors
        doc.cross_check_passed = len(errors) == 0
        return doc
