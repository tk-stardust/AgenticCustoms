"""业务异常定义"""
from shared.errors import (
    AppError, HsClassificationError, TariffLookupError,
    ComplianceCheckError, OriginMatchError, DocumentGenerationError,
)


class TestAppError:
    def test_base_error_with_code(self):
        e = AppError("test", code="TEST")
        assert e.message == "test"
        assert e.code == "TEST"
        assert str(e) == "test"

    def test_default_code(self):
        e = AppError("oops")
        assert e.code == "INTERNAL_ERROR"


class TestSpecificErrors:
    def test_hs_error(self):
        e = HsClassificationError("无法归类")
        assert e.code == "HS_CLASSIFICATION_ERROR"

    def test_tariff_error(self):
        e = TariffLookupError("税率未找到")
        assert e.code == "TARIFF_LOOKUP_ERROR"

    def test_compliance_error(self):
        e = ComplianceCheckError("制裁检查失败")
        assert e.code == "COMPLIANCE_CHECK_ERROR"

    def test_origin_error(self):
        e = OriginMatchError("FTA规则未匹配")
        assert e.code == "ORIGIN_MATCH_ERROR"

    def test_doc_gen_error(self):
        e = DocumentGenerationError("文件生成失败")
        assert e.code == "DOCUMENT_GENERATION_ERROR"
