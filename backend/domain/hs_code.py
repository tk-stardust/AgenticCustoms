from pydantic import BaseModel, Field


class HsCodeResult(BaseModel):
    """HS编码推理结果——由 HS编码推理智能体 产出"""

    code: str = Field(
        ...,
        pattern=r"^\d{6}(\.\d{2,4})?$",
        description="HS编码(至少6位国际通用码)",
    )
    description: str = Field(..., description="品目描述")
    confidence: float = Field(..., ge=0.0, le=1.0, description="推理置信度")
    reasoning_path: list[str] = Field(
        default_factory=list, description="推理步骤链"
    )
    citations: list[str] = Field(
        default_factory=list, description="支撑条文来源(WCO注释/税则条目)"
    )
    alternatives: list["HsCodeResult"] = Field(
        default_factory=list, description="备选编码(置信度较低)"
    )
