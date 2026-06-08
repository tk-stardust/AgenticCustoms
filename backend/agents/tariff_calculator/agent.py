"""关税计算智能体——查税率表 + 试算综合税费"""

from sqlalchemy import select

from domain.tariff_result import TariffResult, TariffItem
from agents.base import BaseAgent
from data.db.database import async_session
from data.db.models import TariffSchedule
from shared.llm import chat
from shared.logger import get_logger

logger = get_logger(__name__)

CALC_PROMPT = """你是一名外贸关税分析师。根据以下信息计算综合税费。

## 输入
HS编码：{hs_code}
目标国家：{country}

## 税率表数据
{schedules}

## 要求
1. 逐项列出：基础关税、增值税、反倾销税（如有）、FTA 优惠税率（如适用）
2. 计算综合税率
3. 如有 FTA 优惠，计算节省金额

## 输出格式（严格JSON）
```json
{{
  "items": [
    {{"name": "基础关税", "rate": 5.0, "note": ""}},
    {{"name": "增值税", "rate": 13.0, "note": ""}}
  ],
  "total_rate": 18.0,
  "fta_applied": null,
  "fta_saving": null
}}
```"""


class TariffCalculatorAgent(BaseAgent[TariffResult]):
    """关税与税费计算智能体"""

    async def run(self, hs_code: str, country: str) -> TariffResult:
        """根据 HS 编码和目标国计算综合税费

        :param hs_code: 前6位 HS 编码
        :param country: 目标国家代码（US/EU/VN 等）
        """
        logger.info("tariff.start", hs_code=hs_code, country=country)

        # 查询匹配的税率表（前缀匹配：如 hs_code=851822 → 匹配 hs_code_prefix=8518）
        async with async_session() as session:
            result = await session.execute(
                select(TariffSchedule).where(
                    TariffSchedule.country == country,
                    TariffSchedule.hs_code_prefix == hs_code[:4],
                )
            )
            rows = result.scalars().all()

        if not rows:
            logger.warning("tariff.no_data", country=country, hs_code=hs_code)
            return TariffResult(
                hs_code=hs_code,
                country=country,
                items=[TariffItem(name="基础关税", rate=0.0, note="无税率数据")],
                total_rate=0.0,
            )

        # 格式化税率数据
        schedules = "\n".join(
            f"- {r.hs_code_prefix}: 基础{r.base_rate}% 增值税{r.vat_rate}% "
            f"反倾销{r.anti_dumping_rate}% FTA:{r.preferential_rate or '—'} ({r.fta_name or '—'})"
            for r in rows
        )

        # LLM 分析与计算
        prompt = CALC_PROMPT.format(hs_code=hs_code, country=country, schedules=schedules)
        messages = [{"role": "user", "content": prompt}]
        response = await chat(messages, temperature=0.1, max_tokens=512)

        result = self._parse_response(response, hs_code, country)
        logger.info("tariff.done", total_rate=result.total_rate)
        return result

    def _parse_response(self, response: str, hs_code: str, country: str) -> TariffResult:
        import json
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return TariffResult(hs_code=hs_code, country=country, items=[], total_rate=0.0)
        fta = data.get("fta_applied")
        # LLM 有时返回 true/false 而非字符串/null，统一处理
        if isinstance(fta, bool) or fta is True or fta is False:
            fta = None
        return TariffResult(
            hs_code=hs_code,
            country=country,
            items=[TariffItem(**i) for i in data.get("items", [])],
            total_rate=data.get("total_rate", 0.0),
            fta_applied=fta,
            fta_saving=data.get("fta_saving"),
        )
