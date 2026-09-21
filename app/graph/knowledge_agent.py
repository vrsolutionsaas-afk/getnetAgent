"""Agente 2 - Knowledge: responde sobre a Getnet via RAG e perguntas gerais via web."""

import logging

from app.graph.llm import llm_geracao
from app.graph.state import AgentState
from app.rag.retriever import recuperar_contexto
from app.tools.web_search import buscar_na_web

logger = logging.getLogger(__name__)

PROMPT_RAG = """Voce e um atendente especialista da Getnet. Responda a pergunta do \
cliente usando SOMENTE as informacoes do contexto abaixo. Seja claro, cordial e \
objetivo. Se o contexto nao contiver a resposta, diga que vai encaminhar para um \
atendente, sem inventar dados.

<contexto>
{contexto}
</contexto>

Pergunta do cliente: {pergunta}"""

PROMPT_WEB = """Voce e um assistente da Getnet. O cliente fez uma pergunta geral \
(fora do dominio de produtos Getnet). Responda de forma breve e util com base no \
resultado de busca abaixo. Deixe claro que e uma informacao geral.

<resultado_busca>
{resultado}
</resultado_busca>

Pergunta do cliente: {pergunta}"""


def _responder_com_web(state: AgentState, trace: list[str]) -> AgentState:
    """Responde usando o web search (Tavily)."""
    pergunta = state["message"]
    resultado = buscar_na_web(pergunta)
    trace.append("knowledge -> web_search")

    if not resultado.sucesso:
        trace.append("web_search -> sem_resultado")
        return {
            **state,
            "response": (
                "Nao consegui obter essa informacao geral agora. Posso ajudar com "
                "duvidas sobre produtos e servicos da Getnet."
            ),
            "agent": "knowledge",
            "sources": [],
            "trace": trace,
        }

    llm = llm_geracao()
    resposta = llm.invoke(
        PROMPT_WEB.format(resultado=resultado.resumo, pergunta=pergunta)
    ).content
    return {
        **state,
        "response": resposta,
        "agent": "knowledge",
        "sources": resultado.fontes,
        "trace": trace,
    }


def knowledge_agent(state: AgentState) -> AgentState:
    """No do grafo: RAG para produtos Getnet, web search para perguntas gerais."""
    trace = state.get("trace", [])
    pergunta = state["message"]
    rota = state.get("route", "produto")

    # Perguntas gerais vao direto para o web search
    if rota == "geral":
        logger.info(
            "knowledge_web",
            extra={"trace_id": state.get("trace_id"), "etapa": "knowledge"},
        )
        return _responder_com_web(state, trace)

    # Rota "produto": tenta o RAG primeiro
    resultado_rag = recuperar_contexto(pergunta)
    if resultado_rag.relevante:
        trace.append("knowledge -> rag")
        llm = llm_geracao()
        resposta = llm.invoke(
            PROMPT_RAG.format(contexto=resultado_rag.contexto, pergunta=pergunta)
        ).content
        logger.info(
            "knowledge_rag",
            extra={"trace_id": state.get("trace_id"), "etapa": "knowledge"},
        )
        return {
            **state,
            "response": resposta,
            "agent": "knowledge",
            "sources": resultado_rag.fontes,
            "trace": trace,
        }

    # Fallback: base sem contexto relevante -> web search
    trace.append("knowledge -> rag_sem_contexto")
    logger.info(
        "knowledge_fallback_web",
        extra={"trace_id": state.get("trace_id"), "etapa": "knowledge"},
    )
    return _responder_com_web(state, trace)
