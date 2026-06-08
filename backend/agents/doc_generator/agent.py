"""申报文件生成智能体——汇总结果 + 生成申报文件 + 交叉校验"""

import json

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
    """归一化 HS 编码——去点后取前6位国际通用码，消除 8518.22 / 85182200 / 851822 格式差异"""
    return code.replace(".", "").strip()[:6]


DOC_PROMPT = """你是一名外贸报关专员。根据归类、关税、合规、原产地分析结果，用纯中文（字段名和内容均为中文）生成一套完整的申报文件，并做交叉校验。

## 商品信息
名称：{name}
描述：{description}
数量：{quantity} 件
申报总价值：{value} 元

## 分析结果
- HS编码：{hs_code}（{hs_desc}，置信度 {confidence}%）
- 关税：综合税率 {tariff_rate}%，FTA 优惠 {fta_applied}
- 合规：风险等级 {risk_level}，{violations}
- 原产地：{origin}

## 输出格式（严格JSON，字段名用英文供程序解析，内容用中文）
```json
{{
  "customs_declaration": {{
    "commodity_name": "{name}",
    "hs_code": "{hs_code}",
    "origin": "中国",
    "quantity": {quantity},
    "unit": "件",
    "declared_value": {value},
    "total_tax_rate": {tariff_rate}
  }},
  "origin_certificate": {{
    "exporter": "待填写",
    "hs_code": "{hs_code}",
    "origin_criteria": "RVC40",
    "fta": "{fta_text}"
  }},
  "compliance_statement": "经核查，本票货物在禁运清单、制裁名单、许可证要求、环保合规方面检查结果如下：{check_items}",
  "cross_check_passed": true,
  "cross_check_errors": []
}}
```

**规则**：
1. JSON 字段名用英文（commodity_name, hs_code 等），内容用中文
2. 依据数量({quantity}件)和申报总价值({value}元)计算税费估算金额 = 总价值 × 综合税率
3. 如任何分析结果缺失或为空，在 compliance_statement 中明确标注"未查到"而非跳过
4. 关税税率与关税计算结果一致
如有矛盾，cross_check_passed 记为 false 并在 cross_check_errors 中列出。"""


class DocGeneratorAgent(BaseAgent[DeclarationDoc]):
    """申报文件生成智能体"""

    async def run(
        self,
        commodity: Commodity,
        hs_result: HsCodeResult,
        tariff_result: TariffResult,
        compliance_result: ComplianceResult,
        origin_result: OriginResult,
    ) -> DeclarationDoc:
        """生成申报文件并交叉校验

        :param commodity: 商品实体
        :param hs_result: HS 归类结果
        :param tariff_result: 关税计算结果
        :param compliance_result: 合规校验结果
        :param origin_result: 原产地匹配结果
        """
        logger.info("doc_gen.start", name=commodity.name)

        origin_text = (
            f"推荐原产地 {origin_result.recommended_origin or 'CN'}，"
            f"适用 {', '.join(origin_result.applicable_ftas) or '无 FTA'}，"
            f"满足 {', '.join(origin_result.meeting_criteria) or '—'}"
        )

        prompt = DOC_PROMPT.format(
            name=commodity.name,
            description=commodity.description,
            quantity=commodity.quantity,
            value=commodity.declared_value,
            hs_code=hs_result.code,
            hs_desc=hs_result.description,
            confidence=hs_result.confidence,
            tariff_rate=tariff_result.total_rate,
            fta_applied=tariff_result.fta_applied or "无",
            fta_text=tariff_result.fta_applied or "不适用",
            check_items=compliance_result.summary,
            risk_level=compliance_result.risk_level.value,
            violations=f"违规 {len(compliance_result.violations)} 项" if compliance_result.violations else "无违规",
            origin=origin_text,
        )
        messages = [{"role": "user", "content": prompt}]
        response = await chat(messages, temperature=0.1, max_tokens=1024)

        result = self._parse_response(response)
        result = self._cross_validate(result, hs_result, tariff_result, compliance_result)
        logger.info("doc_gen.done", cross_ok=result.cross_check_passed)
        return result

    def _parse_response(self, response: str) -> DeclarationDoc:
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return DeclarationDoc(
                customs_declaration={},
                compliance_statement="LLM 响应解析失败",
                cross_check_passed=False,
                cross_check_errors=["LLM 输出非 JSON 格式"],
            )
        return DeclarationDoc(**data)

    def _cross_validate(
        self,
        doc: DeclarationDoc,
        hs: HsCodeResult,
        tariff: TariffResult,
        compliance: ComplianceResult,
    ) -> DeclarationDoc:
        """验证申报文件与各分析结果的一致性"""
        errors = list(doc.cross_check_errors or [])

        # HS 编码一致性——归一化后比较前6位，兼容 851822 / 8518.22 / 85182200 等格式
        decl_hs = doc.customs_declaration.get("hs_code", "")
        if decl_hs and _normalize_hs(str(decl_hs)) != _normalize_hs(hs.code):
            errors.append(f"报关单HS编码 {decl_hs} 与归类结果 {hs.code} 不一致")

        # 原产地证书 HS 一致性
        if doc.origin_certificate:
            cert_hs = doc.origin_certificate.get("hs_code", "")
            if cert_hs and _normalize_hs(str(cert_hs)) != _normalize_hs(hs.code):
                errors.append(f"原产地证书HS编码 {cert_hs} 与归类结果 {hs.code} 不一致")

        # 税率一致性
        decl_tax = doc.customs_declaration.get("total_tax_rate", 0)
        if isinstance(decl_tax, (int, float)) and abs(decl_tax - tariff.total_rate) > 1.0:
            errors.append(f"报关单综合税率 {decl_tax}% 与计算结果 {tariff.total_rate}% 不一致")

        doc.cross_check_errors = errors
        doc.cross_check_passed = len(errors) == 0
        return doc
