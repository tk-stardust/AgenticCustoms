"""原产地匹配智能体——FTA 规则匹配 + 最优策略推荐"""

import json

from sqlalchemy import select

from domain.origin_result import OriginResult
from agents.base import BaseAgent
from data.db.database import async_session
from data.db.models import TariffSchedule
from shared.llm import chat, parse_llm_json
from shared.logger import get_logger

logger = get_logger(__name__)

ORIGIN_PROMPT = """你是一名原产地规则专家，精通 RCEP、USMCA、中欧 FTA 等自贸协定的原产地标准。

## 任务
根据商品的 HS 编码和目标国，判断可以适用哪些 FTA 优惠税率，推荐最优原产地申报策略。

## 输入
HS编码：{hs_code}
目标国家：{country}
FTA税率数据：{fta_data}

## 原产地判定标准（常用）
- RVC（区域价值成分）：产品在成员国生产的价值占比 ≥ 40%
- CTC（税则归类改变）：加工后品目改变（CTH），前4位改变
- PSR（产品特定规则）：特定商品的额外要求

## 输出格式（严格JSON）
```json
{{
  "applicable_ftas": ["RCEP"],
  "recommended_origin": "CN",
  "meeting_criteria": ["RVC40: 区域价值成分≥40%"],
  "rvc_percentage": null,
  "note": "建议以中国原产地申报"
}}
```"""


class OriginMatcherAgent(BaseAgent[OriginResult]):
    """原产地规则匹配智能体"""

    async def run(self, hs_code: str, country: str) -> OriginResult:
        """匹配 FTA 优惠税率，推荐原产地申报策略

        :param hs_code: HS 编码
        :param country: 目标国家代码
        """
        logger.info("origin.start", hs_code=hs_code, country=country)

        # 查询带 FTA 的税率
        async with async_session() as session:
            result = await session.execute(
                select(TariffSchedule).where(
                    TariffSchedule.country == country,
                    TariffSchedule.hs_code_prefix.like(hs_code[:4] + "%"),
                    TariffSchedule.fta_name.isnot(None),
                )
            )
            rows = result.scalars().all()

        fta_data = "\n".join(
            f"- {r.fta_name}: 基础{r.base_rate}% → 优惠{r.preferential_rate}%"
            for r in rows
        ) if rows else "无 FTA 优惠税率数据"

        prompt = ORIGIN_PROMPT.format(hs_code=hs_code, country=country, fta_data=fta_data)
        messages = [{"role": "user", "content": prompt}]
        response = await chat(messages, temperature=0.1, max_tokens=1024)

        result = self._parse_response(response, hs_code)
        logger.info("origin.done", ftas=result.applicable_ftas)
        return result

    def _parse_response(self, response: str, hs_code: str) -> OriginResult:
        try:
            data = parse_llm_json(response)
        except json.JSONDecodeError:
            logger.error("origin.parse_failed", raw_response=response[:500])
            return OriginResult(hs_code=hs_code, note="LLM 响应解析失败")
        return OriginResult(
            hs_code=hs_code,
            applicable_ftas=data.get("applicable_ftas", []),
            recommended_origin=data.get("recommended_origin"),
            meeting_criteria=data.get("meeting_criteria", []),
            rvc_percentage=data.get("rvc_percentage"),
            note=data.get("note", ""),
        )
