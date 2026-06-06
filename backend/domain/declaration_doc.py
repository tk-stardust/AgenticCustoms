from pydantic import BaseModel, Field


class DeclarationDoc(BaseModel):
    """申报文件——由 申报文件生成智能体 产出"""

    customs_declaration: dict = Field(
        default_factory=dict, description="报关单草单(结构化JSON)"
    )
    origin_certificate: dict | None = Field(
        default=None, description="原产地证书申请书"
    )
    compliance_statement: str = Field(
        default="", description="合规声明文本"
    )
    cross_check_passed: bool = Field(
        default=False, description="交叉校验是否通过"
    )
    cross_check_errors: list[str] = Field(
        default_factory=list, description="交叉校验发现的矛盾项"
    )
