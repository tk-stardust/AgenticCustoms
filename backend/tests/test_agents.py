"""Agent 测试——mock LLM 和 DB 返回"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from domain.commodity import Commodity
from domain.hs_code import HsCodeResult
from domain.tariff_result import TariffResult
from domain.compliance_result import ComplianceResult, RiskLevel
from domain.origin_result import OriginResult
from domain.declaration_doc import DeclarationDoc


def _mock_db(return_rows=None):
    """构造 mock DB 会话，链式 execute → scalars → all 返回指定列表"""
    rows = return_rows or []
    session = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = rows
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    return session


@pytest.fixture
def commodity():
    return Commodity(name="蓝牙音箱", description="塑料外壳音箱", material="塑料",
                     function="音乐播放", usage="家庭娱乐")


class TestTariffCalculator:
    @pytest.mark.asyncio
    async def test_parse_tariff_response(self, commodity):
        from agents.tariff_calculator.agent import TariffCalculatorAgent
        agent = TariffCalculatorAgent()

        mock_response = json.dumps({
            "items": [{"name": "基础关税", "rate": 5.0, "note": ""}],
            "total_rate": 5.0,
        })

        with patch("agents.tariff_calculator.agent.chat", new=AsyncMock(return_value=mock_response)):
            result = await agent.run("851822", "US")
            assert isinstance(result, TariffResult)
            assert result.total_rate == 5.0
            assert result.hs_code == "851822"

    @pytest.mark.asyncio
    async def test_coerce_bool_fta_applied(self, commodity):
        from agents.tariff_calculator.agent import TariffCalculatorAgent
        agent = TariffCalculatorAgent()
        mock_data = {"items": [], "total_rate": 0.0, "fta_applied": True}
        data = agent._parse_response(json.dumps(mock_data), "851822", "US")
        assert data.fta_applied is None


class TestComplianceChecker:
    @pytest.mark.asyncio
    async def test_compliance_check_returns_result(self, commodity):
        from agents.compliance_checker.agent import ComplianceCheckerAgent
        agent = ComplianceCheckerAgent()

        mock_response = json.dumps({
            "risk_level": "green", "violations": [], "license_required": False,
            "sanctions_hit": False, "summary": "合规，无风险",
        })
        mock_db = _mock_db([])

        with patch("agents.compliance_checker.agent.chat", new=AsyncMock(return_value=mock_response)), \
             patch("agents.compliance_checker.agent.async_session", return_value=mock_db):
            result = await agent.run(commodity, "851822", "US")
            assert isinstance(result, ComplianceResult)
            assert result.risk_level == RiskLevel.GREEN


class TestDocGenerator:
    @pytest.mark.asyncio
    async def test_cross_validate_hs_mismatch(self):
        from agents.doc_generator.agent import DocGeneratorAgent
        agent = DocGeneratorAgent()

        doc = DeclarationDoc(
            customs_declaration={"hs_code": "847130"},
            compliance_statement="ok",
            cross_check_passed=True,
        )
        hs = HsCodeResult(code="851822", description="音箱", confidence=0.95)
        tariff = TariffResult(hs_code="851822", country="US", items=[], total_rate=5.0)
        comp = ComplianceResult()

        result = agent._cross_validate(doc, hs, tariff, comp)
        assert result.cross_check_passed is False
        assert any("847130" in e for e in result.cross_check_errors)


class TestOriginMatcher:
    @pytest.mark.asyncio
    async def test_origin_matching(self):
        from agents.origin_matcher.agent import OriginMatcherAgent
        agent = OriginMatcherAgent()

        mock_response = json.dumps({
            "applicable_ftas": ["RCEP"], "recommended_origin": "CN",
            "meeting_criteria": ["RVC40"], "note": "符合RCEP原产地规则",
        })
        mock_db = _mock_db([])

        with patch("agents.origin_matcher.agent.chat", new=AsyncMock(return_value=mock_response)), \
             patch("agents.origin_matcher.agent.async_session", return_value=mock_db):
            result = await agent.run("851822", "US")
            assert isinstance(result, OriginResult)
            assert "RCEP" in result.applicable_ftas
