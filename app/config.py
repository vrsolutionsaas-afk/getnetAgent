"""Configuracao central da aplicacao, carregada de variaveis de ambiente (.env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracao(BaseSettings):
    """Configuracoes da aplicacao lidas do ambiente."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # OpenAI
    openai_api_key: str = ""

    # Tavily
    tavily_api_key: str = ""

    # Banco de dados (pgvector)
    postgres_user: str = "getnet"
    postgres_password: str = "getnet"
    postgres_db: str = "getnet_rag"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Modelos
    modelo_roteamento: str = "gpt-4o-mini"
    modelo_geracao: str = "gpt-4o"
    modelo_embedding: str = "text-embedding-3-small"

    # RAG
    rag_limiar_similaridade: float = 0.5
    rag_top_k: int = 4

    # App
    log_level: str = "INFO"

    @property
    def url_postgres(self) -> str:
        """URL de conexao no formato aceito pelo langchain-postgres (psycopg3)."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def obter_config() -> Configuracao:
    """Retorna a instancia unica (cacheada) de configuracao."""
    return Configuracao()
