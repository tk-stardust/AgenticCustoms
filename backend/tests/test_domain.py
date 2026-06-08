"""领域实体校验"""
import pytest
from domain.commodity import Commodity
from domain.hs_code import HsCodeResult
from domain.tariff_result import TariffResult, TariffItem
from domain.compliance_result import ComplianceResult, Violation
from domain.enums import RiskLevel
from domain.declaration_doc import DeclarationDoc


class TestCommodity:
    def test_create_valid(self):
        c = Commodity(name="蓝牙音箱", description="便携式音箱")
        assert c.name == "蓝牙音箱"
        assert c.to_rag_query() == "蓝牙音箱"

    def test_rag_query_with_all_fields(self):
        c = Commodity(name="音箱", material="塑料", function="播放", usage="家用", description="塑料音箱")
        assert "材质:塑料" in c.to_rag_query()
        assert "功能:播放" in c.to_rag_query()

    def test_empty_name_raises(self):
        with pytest.raises(Exception):
            Commodity(name="", description="x")


class TestHsCodeResult:
    def test_valid_code(self):
        r = HsCodeResult(code="851822", description="音箱", confidence=0.95)
        assert r.code == "851822"

    def test_invalid_code_too_short(self):
        with pytest.raises(Exception):
            HsCodeResult(code="123", description="x", confidence=0.5)

    def test_confidence_range(self):
        HsCodeResult(code="851822", description="x", confidence=0.0)
        HsCodeResult(code="851822", description="x", confidence=1.0)
        with pytest.raises(Exception):
            HsCodeResult(code="851822", description="x", confidence=2.0)


class TestTariffResult:
    def test_create(self):
        r = TariffResult(
            hs_code="851822", country="US",
            items=[TariffItem(name="基础关税", rate=5.0)],
            total_rate=5.0,
        )
        assert r.total_rate == 5.0

    def test_with_fta(self):
        r = TariffResult(hs_code="851822", country="US", items=[], total_rate=0.0, fta_applied="RCEP")
        assert r.fta_applied == "RCEP"


class TestComplianceResult:
    def test_default_green(self):
        r = ComplianceResult()
        assert r.risk_level == RiskLevel.GREEN

    def test_with_violations(self):
        r = ComplianceResult(
            risk_level=RiskLevel.RED,
            violations=[Violation(category="制裁", description="命中OFAC", severity=RiskLevel.RED)]
        )
        assert len(r.violations) == 1
        assert r.violations[0].category == "制裁"


class TestDeclarationDoc:
    def test_create(self):
        d = DeclarationDoc(
            customs_declaration={"hs_code": "851822"},
            compliance_statement="通过",
            cross_check_passed=True,
        )
        assert d.cross_check_passed is True
