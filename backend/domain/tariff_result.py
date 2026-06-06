from pydantic import BaseModel, Field


class TariffItem(BaseModel):
    """单条税费项"""

    name: str = Field(..., description="税项名称, 如'基础关税'/'增值税'/'反倾销税'")
    rate: float = Field(..., ge=0.0, description="税率")
    amount: float | None = Field(default=None, description="估算税额")
    note: str = Field(default="", description="备注")


class TariffResult(BaseModel):
    """关税计算结果——由 关税计算智能体 产出"""

    hs_code: str = Field(..., description="所依据的HS编码")
    country: str = Field(..., description="目标国家代码")
    items: list[TariffItem] = Field(default_factory=list, description="税费明细")
    total_rate: float = Field(default=0.0, description="综合税率(%)")
    total_amount: float | None = Field(default=None, description="综合税额估算")
    fta_applied: str | None = Field(default=None, description="适用的FTA,如'RCEP'")
    fta_saving: float | None = Field(default=None, description="FTA优惠节省税额")
