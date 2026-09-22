"""Aplicacao FastAPI: expoe o endpoint POST /chat da orquestracao multi-agente."""

import logging

from fastapi import FastAPI, Header, HTTPException

from app.config import obter_config
from app.graph.builder import construir_grafo
from app.graph.state import AgentState
from app.observability.logging import (
    configurar_logging,
    novo_trace_id,
)
from app.rag.ingest import executar_ingestao
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


@app.post("/admin/ingest")
def admin_ingest(x_admin_token: str = Header(default="")) -> dict:
    """Dispara a ingestao da base de conhecimento (uso administrativo).

    Protegido por token (header X-Admin-Token == ADMIN_TOKEN). Util em ambientes
    gerenciados (Railway) onde nao ha terminal para rodar o script de ingestao.
    """
    config = obter_config()
    if not config.admin_token:
        raise HTTPException(status_code=403, detail="Endpoint de ingestao desativado.")
    if x_admin_token != config.admin_token:
        raise HTTPException(status_code=401, detail="Token invalido.")

    total = executar_ingestao()
    return {"status": "ok", "chunks_inseridos": total}


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
