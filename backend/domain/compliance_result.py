from pydantic import BaseModel, Field

from .enums import RiskLevel


class Violation(BaseModel):
    """单条合规违规项"""

    category: str = Field(
        ..., description="违规类别: sanctions/prohibited/license_required/environmental"
    )
    description: str = Field(..., description="违规描述")
    severity: RiskLevel = Field(..., description="严重程度")
    source: str = Field(default="", description="法规来源")


class ComplianceResult(BaseModel):
    """合规校验结果——由 合规校验智能体 产出"""

    risk_level: RiskLevel = Field(default=RiskLevel.GREEN, description="综合风险等级")
    violations: list[Violation] = Field(
        default_factory=list, description="违规项列表"
    )
    license_required: bool = Field(default=False, description="是否需要进出口许可证")
    license_type: str | None = Field(default=None, description="许可证类型")
    sanctions_hit: bool = Field(default=False, description="是否命中制裁清单")
    summary: str = Field(default="", description="合规结论概述")
