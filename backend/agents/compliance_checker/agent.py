"""合规校验智能体——制裁清单匹配 + LLM 风险评估"""

import json

from sqlalchemy import select

from domain.commodity import Commodity
from domain.compliance_result import ComplianceResult, Violation
from domain.enums import RiskLevel
from agents.base import BaseAgent
from data.db.database import async_session
from data.db.models import SanctionEntry
from shared.llm import chat
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

## 评估维度
1. 是否命中制裁实体清单
2. 是否属于禁限品（武器、敏感技术、濒危物种等）
3. 是否需要出口许可证
4. 是否涉及环保法规（RoHS/REACH等）

## 输出格式（严格JSON）
```json
{{
  "risk_level": "green",
  "violations": [],
  "license_required": false,
  "license_type": null,
  "sanctions_hit": false,
  "summary": "合规评估概述"
}}
```"""


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
        response = await chat(messages, temperature=0.1, max_tokens=512)

        result = self._parse_response(response)
        logger.info("compliance.done", risk=result.risk_level)
        return result

    def _parse_response(self, response: str) -> ComplianceResult:
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return ComplianceResult(risk_level=RiskLevel.YELLOW, summary="LLM 响应解析失败，请人工审核")
        return ComplianceResult(
            risk_level=RiskLevel(data.get("risk_level", "green")),
            violations=[Violation(**v) for v in data.get("violations", [])],
            license_required=data.get("license_required", False),
            license_type=data.get("license_type"),
            sanctions_hit=data.get("sanctions_hit", False),
            summary=data.get("summary", ""),
        )
