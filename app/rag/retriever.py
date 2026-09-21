"""Recuperacao de contexto do RAG com filtro por limiar de similaridade."""

import logging
from dataclasses import dataclass, field

from app.config import obter_config
from app.rag.vectorstore import obter_vectorstore

logger = logging.getLogger(__name__)


@dataclass
class ResultadoRAG:
    """Resultado de uma consulta ao RAG."""

    contexto: str = ""
    fontes: list[str] = field(default_factory=list)
    relevante: bool = False


def recuperar_contexto(pergunta: str) -> ResultadoRAG:
    """Busca trechos relevantes na base Getnet.

    Usa similarity_search_with_relevance_scores (scores normalizados 0-1) e
    aplica o limiar configurado. Se nenhum trecho passar do limiar, marca
    relevante=False para que o agente use o web search como fallback.
    """
    config = obter_config()
    vectorstore = obter_vectorstore()

    try:
        resultados = vectorstore.similarity_search_with_relevance_scores(
            pergunta, k=config.rag_top_k
        )
    except Exception as exc:  # noqa: BLE001 - falha de RAG nao pode derrubar o agente
        logger.warning("Falha na consulta ao RAG: %s", exc)
        return ResultadoRAG()

    trechos: list[str] = []
    fontes: list[str] = []
    for doc, score in resultados:
        if score < config.rag_limiar_similaridade:
            continue
        trechos.append(doc.page_content)
        fonte = doc.metadata.get("source")
        if fonte and fonte not in fontes:
            fontes.append(fonte)

    if not trechos:
        logger.info("RAG sem trechos acima do limiar para: %s", pergunta[:60])
        return ResultadoRAG()

    return ResultadoRAG(
        contexto="\n\n---\n\n".join(trechos), fontes=fontes, relevante=True
    )
