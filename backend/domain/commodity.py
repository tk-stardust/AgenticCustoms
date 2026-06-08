from pydantic import BaseModel, Field


class Commodity(BaseModel):
    """商品实体——Agentic RAG推理的输入"""

    name: str = Field(..., min_length=1, max_length=500, description="商品名称")
    material: str | None = Field(default=None, description="材质")
    function: str | None = Field(default=None, description="功能用途")
    usage: str | None = Field(default=None, description="应用场景")
    description: str = Field(..., min_length=1, description="原始商品描述")
    quantity: int = Field(default=1, ge=1, description="货物数量（件）")
    declared_value: float = Field(default=0.0, ge=0, description="申报价值（元/美元）")
    image_url: str | None = Field(default=None, description="商品图片URL(OCR辅助)")

    def to_rag_query(self) -> str:
        """组合属性生成 RAG 检索查询文本"""
        parts = [self.name]
        if self.material:
            parts.append(f"材质:{self.material}")
        if self.function:
            parts.append(f"功能:{self.function}")
        if self.usage:
            parts.append(f"用途:{self.usage}")
        return "，".join(parts)
