from pydantic import BaseModel, Field


class OriginResult(BaseModel):
    """原产地匹配结果——由 原产地匹配智能体 产出"""

    hs_code: str = Field(..., description="所依据的HS编码")
    applicable_ftas: list[str] = Field(
        default_factory=list, description="可适用的FTA列表"
    )
    recommended_origin: str | None = Field(
        default=None, description="推荐申报原产地"
    )
    meeting_criteria: list[str] = Field(
        default_factory=list, description="满足的原产地标准(RVC40/CTC/PSR等)"
    )
    rvc_percentage: float | None = Field(
        default=None, ge=0.0, le=100.0, description="区域价值成分百分比"
    )
    note: str = Field(default="", description="补充说明")
