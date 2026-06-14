"""合规校验智能体——制裁清单匹配 + LLM 风险评估"""

import json

from sqlalchemy import select

from domain.commodity import Commodity
from domain.compliance_result import ComplianceResult, Violation
from domain.enums import RiskLevel
from agents.base import BaseAgent
from data.db.database import async_session
from data.db.models import SanctionEntry
from shared.llm import chat, parse_llm_json
from shared.logger import get_logger

logger = get_logger(__name__)

COMPLIANCE_PROMPT = """你是一名外贸合规专家，精通各国进出口管制法规和制裁清单。

## 任务
根据商品信息和制裁名单检索结果，评估该商品出口到目标国家的合规风险。

## 商品信息
名称：{name}
描述：{description}
HS编码：{hs_code}
目标国家：{country}

## 制裁名单检索结果
{sanctions}

## 评估维度（逐项出具结论）
1. 禁运清单：检查是否列入禁运品目录 → 通过/未通过/未查到数据
2. 制裁名单：检查是否匹配制裁实体 → 通过/未通过/未查到数据
3. 出口许可证：是否需要出口许可 → 不需要/需要（注明类型）/未查到数据
4. 环保法规：RoHS/REACH等 → 不适用/需合规/未查到数据

## 输出格式（严格JSON，中文）
```json
{{
  "risk_level": "green/yellow/red",
  "violations": [{{"category": "禁运/制裁/许可证/环保", "description": "具体说明", "severity": "red/yellow/green", "source": "数据来源"}}],
  "license_required": false,
  "license_type": null,
  "sanctions_hit": false,
  "check_items": {{
    "禁运清单": "✅ 未命中",
    "制裁名单": "⚠️ 当前制裁库仅含 200 条 OFAC 数据，未覆盖全部实体，请人工复核",
    "出口许可证": "✅ 不需要",
    "环保合规": "⚠️ 未查到目标国 RoHS/REACH 数据，请人工确认"
  }},
  "summary": "逐项评估结论"
}}
```

**规则**：如制裁库只有 200 条数据，必须在"制裁名单"中标注"当前仅含部分数据，请人工复核"。任何维度缺少数据，标注"未查到"而非跳过。"""


class ComplianceCheckerAgent(BaseAgent[ComplianceResult]):
    """合规与禁限品校验智能体"""

    async def run(self, commodity: Commodity, hs_code: str, country: str) -> ComplianceResult:
        """校验商品出口合规风险

        :param commodity: 商品实体
        :param hs_code: HS 编码
        :param country: 目标国家代码
        """
        logger.info("compliance.start", name=commodity.name, country=country)

        # 查询制裁清单
        async with async_session() as session:
            result = await session.execute(select(SanctionEntry))
            rows = result.scalars().all()

        sanctions_text = "\n".join(
            f"- {r.entity_name}（{r.country}）: {r.list_type} → {r.restriction_type}"
            for r in rows
        ) if rows else "无制裁记录"

        # LLM 分析
        prompt = COMPLIANCE_PROMPT.format(
            name=commodity.name,
            description=commodity.description,
            hs_code=hs_code,
            country=country,
            sanctions=sanctions_text,
        )
        messages = [{"role": "user", "content": prompt}]
        response = await chat(messages, temperature=0.1, max_tokens=1024)

        result = self._parse_response(response)
        logger.info("compliance.done", risk=result.risk_level)
        return result

    def _parse_response(self, response: str) -> ComplianceResult:
        try:
            data = parse_llm_json(response)
        except json.JSONDecodeError:
            logger.error("compliance.parse_failed", raw_response=response[:500])
            return ComplianceResult(risk_level=RiskLevel.YELLOW, summary="LLM 响应解析失败，请人工审核")
        return ComplianceResult(
            risk_level=RiskLevel(data.get("risk_level", "green")),
            violations=[Violation(**v) for v in data.get("violations", [])],
            license_required=data.get("license_required", False),
            license_type=data.get("license_type"),
            sanctions_hit=data.get("sanctions_hit", False),
            summary=data.get("summary", ""),
        )
