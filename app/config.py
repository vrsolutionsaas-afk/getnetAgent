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
    # Em producao (Railway) basta definir DATABASE_URL; ele tem prioridade sobre
    # os campos POSTGRES_* usados no docker-compose/local.
    database_url: str = ""
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

    # Token para o endpoint administrativo de ingestao (vazio = endpoint desativado)
    admin_token: str = ""

    @property
    def url_postgres(self) -> str:
        """URL de conexao no formato aceito pelo langchain-postgres (psycopg3).

        Se DATABASE_URL estiver definida (ex.: Railway), normaliza o schema para
        'postgresql+psycopg://'. Caso contrario, monta a URL a partir dos campos
        POSTGRES_* (docker-compose / local).
        """
        if self.database_url:
            url = self.database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def obter_config() -> Configuracao:
    """Retorna a instancia unica (cacheada) de configuracao."""
    return Configuracao()
