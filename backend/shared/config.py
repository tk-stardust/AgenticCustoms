from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "dev"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "agentic"
    mysql_password: str = ""
    mysql_database: str = "agentic_customs"

    # Chroma
    chroma_persist_dir: str = "./chroma_data"
    chroma_collection: str = "customs_knowledge"

    # LLM — DashScope（优先读 DASHSCOPE_API_KEY，兼容 LLM_API_KEY）
    llm_model: str = "qwen-plus"
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DASHSCOPE_API_KEY", "LLM_API_KEY"),
    )
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Embedding
    embedding_model: str = "bge-base-zh-v1.5"
    embedding_model_path: str = ""  # 本地模型路径，空则从HF下载

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    # 从 backend/ 运行时，../ 指向项目根目录，读取统一的 .env
    model_config = dict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
