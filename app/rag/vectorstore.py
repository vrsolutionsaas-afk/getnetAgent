"""Conexao com o vector store pgvector (via langchain-postgres)."""

from functools import lru_cache

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from app.config import obter_config

# Nome da colecao (tabela logica) onde ficam os embeddings da base Getnet
NOME_COLECAO = "getnet_knowledge"


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
