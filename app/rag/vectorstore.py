"""Conexao com o vector store pgvector (via langchain-postgres)."""

import logging
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from app.config import obter_config

logger = logging.getLogger(__name__)

# Nome da colecao (tabela logica) onde ficam os embeddings da base Getnet
NOME_COLECAO = "getnet_knowledge"


def garantir_extensao_vector() -> None:
    """Garante que a extensao pgvector exista no banco.

    No docker-compose a extensao ja e criada pelo init.sql, mas em provedores
    gerenciados (ex.: Railway) precisamos cria-la em runtime. Best-effort.
    """
    import psycopg

    config = obter_config()
    # psycopg.connect usa o schema padrao 'postgresql://' (sem o +psycopg do SQLAlchemy)
    dsn = config.url_postgres.replace("postgresql+psycopg://", "postgresql://")
    try:
        with psycopg.connect(dsn, autocommit=True) as conexao:
            conexao.execute("CREATE EXTENSION IF NOT EXISTS vector")
        logger.info("Extensao pgvector garantida.")
    except Exception as exc:  # noqa: BLE001 - best-effort
        logger.warning("Nao foi possivel garantir a extensao pgvector: %s", exc)


@lru_cache
def obter_embeddings() -> OpenAIEmbeddings:
    """Retorna o modelo de embeddings configurado."""
    config = obter_config()
    return OpenAIEmbeddings(
        model=config.modelo_embedding, api_key=config.openai_api_key
    )


def obter_vectorstore() -> PGVector:
    """Retorna a instancia do PGVector conectada ao Postgres.

    use_jsonb=True armazena os metadados como JSONB (consultas mais eficientes).
    """
    config = obter_config()
    return PGVector(
        embeddings=obter_embeddings(),
        collection_name=NOME_COLECAO,
        connection=config.url_postgres,
        use_jsonb=True,
    )
