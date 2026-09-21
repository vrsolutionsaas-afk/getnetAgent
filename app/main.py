"""Aplicacao FastAPI: expoe o endpoint POST /chat da orquestracao multi-agente."""

import logging

from fastapi import FastAPI

from app.graph.builder import construir_grafo
from app.graph.state import AgentState
from app.observability.logging import (
    configurar_logging,
    novo_trace_id,
)
from app.schemas import ChatRequest, ChatResponse

configurar_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Getnet Multi-Agent Support",
    description=(
        "Sistema multi-agente de suporte da Getnet (Router, Knowledge, Support, "
        "Escalation) orquestrado com LangGraph."
    ),
    version="1.0.0",
)


@app.get("/health")
def health() -> dict:
    """Healthcheck simples."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    """Processa uma mensagem do usuario pela orquestracao multi-agente."""
    trace_id = novo_trace_id()
    logger.info(
        "request_recebido",
        extra={
            "trace_id": trace_id,
            "etapa": "entrada",
            "detalhe": payload.user_id,
        },
    )

    estado_inicial: AgentState = {
        "message": payload.message,
        "user_id": payload.user_id,
        "trace_id": trace_id,
        "trace": [],
        "sources": [],
        "escalated": False,
    }

    grafo = construir_grafo()
    estado_final: AgentState = grafo.invoke(estado_inicial)

    logger.info(
        "request_concluido",
        extra={
            "trace_id": trace_id,
            "etapa": "saida",
            "detalhe": estado_final.get("agent"),
        },
    )

    return ChatResponse(
        response=estado_final.get("response", ""),
        agent=estado_final.get("agent", "desconhecido"),
        route=estado_final.get("route", "desconhecido"),
        sources=estado_final.get("sources", []),
        escalated=estado_final.get("escalated", False),
        trace_id=trace_id,
        trace=estado_final.get("trace", []),
    )
