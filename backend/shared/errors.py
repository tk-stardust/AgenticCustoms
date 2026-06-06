class AppError(Exception):
    """应用基类异常——所有业务异常由此派生"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class HsClassificationError(AppError):
    """HS编码归类失败"""
    def __init__(self, message: str):
        super().__init__(message, code="HS_CLASSIFICATION_ERROR")


class TariffLookupError(AppError):
    """关税查询失败"""
    def __init__(self, message: str):
        super().__init__(message, code="TARIFF_LOOKUP_ERROR")


class ComplianceCheckError(AppError):
    """合规校验失败"""
    def __init__(self, message: str):
        super().__init__(message, code="COMPLIANCE_CHECK_ERROR")


class OriginMatchError(AppError):
    """原产地匹配失败"""
    def __init__(self, message: str):
        super().__init__(message, code="ORIGIN_MATCH_ERROR")


class DocumentGenerationError(AppError):
    """申报文件生成失败"""
    def __init__(self, message: str):
        super().__init__(message, code="DOCUMENT_GENERATION_ERROR")


class RagRetrievalError(AppError):
    """RAG检索失败"""
    def __init__(self, message: str):
        super().__init__(message, code="RAG_RETRIEVAL_ERROR")
