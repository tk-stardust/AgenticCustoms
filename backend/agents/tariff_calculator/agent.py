"""关税计算智能体——查税率表 + LLM 分析税费"""

from sqlalchemy import select

from domain.tariff_result import TariffResult, TariffItem
from agents.base import BaseAgent
from data.db.database import async_session
from data.db.models import TariffSchedule
from shared.llm import chat
from shared.logger import get_logger

logger = get_logger(__name__)

CALC_PROMPT = """你是一名外贸关税分析师。根据以下信息分析适用的税费项目。

## 输入
HS编码：{hs_code}
目标国家：{country}
货物数量：{quantity} 件
申报总价值：{declared_value} 元

## 税率表数据
{schedules}

## 要求
1. 逐项列出：基础关税、增值税、反倾销税（如有）、FTA 优惠税率（如适用）
2. 综合税率 = 各项税率之和
3. 如有 FTA 优惠，填写 fta_applied（FTA名称）和 fta_saving（税率差额，百分点）
4. 如果申报价值为 0，note 注明"未提供申报价值"
5. 金额计算由程序完成，你只需输出税率

## 输出格式（严格JSON）
```json
{{
  "items": [
    {{"name": "基础关税", "rate": 5.0, "note": ""}},
    {{"name": "增值税", "rate": 13.0, "note": ""}}
  ],
  "total_rate": 18.0,
  "fta_applied": null,
  "fta_saving": null,
  "data_missing": false
}}
```"""


class TariffCalculatorAgent(BaseAgent[TariffResult]):
    """关税与税费计算智能体"""

    async def run(self, hs_code: str, country: str,
                  declared_value: float = 0.0, quantity: int = 1) -> TariffResult:
        logger.info("tariff.start", hs_code=hs_code, country=country,
                    value=declared_value, qty=quantity)

        async with async_session() as session:
            result = await session.execute(
                select(TariffSchedule).where(
                    TariffSchedule.country == country,
                    TariffSchedule.hs_code_prefix.like(hs_code[:4] + "%"),
                ).order_by(TariffSchedule.hs_code_prefix.desc())
            )
            rows = result.scalars().all()

        if not rows:
            logger.warning("tariff.no_data", country=country, hs_code=hs_code)
            return TariffResult(
                hs_code=hs_code, country=country,
                items=[
                    TariffItem(name="基础关税", rate=0.0, note="⚠ 未查到税率数据"),
                    TariffItem(name="增值税", rate=0.0, note="⚠ 未查到税率数据"),
                    TariffItem(name="反倾销税", rate=0.0, note="⚠ 未查到税率数据"),
                ],
                total_rate=0.0,
                data_missing=True,
            )

        schedules = "\n".join(
            f"- {r.hs_code_prefix}: 基础{r.base_rate}% 增值税{r.vat_rate}% "
            f"反倾销{r.anti_dumping_rate}% FTA:{r.preferential_rate or '—'} ({r.fta_name or '—'})"
            for r in rows
        )

        prompt = CALC_PROMPT.format(
            hs_code=hs_code, country=country, schedules=schedules,
            declared_value=declared_value, quantity=quantity)
        messages = [{"role": "user", "content": prompt}]
        response = await chat(messages, temperature=0.1, max_tokens=512)

        result = self._parse_response(response, hs_code, country, declared_value)
        logger.info("tariff.done", total_rate=result.total_rate)
        return result

    def _parse_response(self, response: str, hs_code: str, country: str,
                         declared_value: float = 0.0) -> TariffResult:
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
        if isinstance(fta, bool) or fta is True or fta is False:
            fta = None
        items = []
        total_amount = 0.0
        for i in data.get("items", []):
            amount = round(declared_value * i.get("rate", 0.0) / 100, 2)
            total_amount += amount
            items.append(TariffItem(
                name=i.get("name", ""),
                rate=i.get("rate", 0.0),
                amount=amount,
                note=i.get("note", ""),
            ))
        return TariffResult(
            hs_code=hs_code,
            country=country,
            items=items,
            total_rate=data.get("total_rate", 0.0),
            total_amount=total_amount,
            fta_applied=fta,
            fta_saving=data.get("fta_saving"),
            data_missing=data.get("data_missing", False),
        )
