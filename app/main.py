"""Aplicacao FastAPI: expoe o endpoint POST /chat da orquestracao multi-agente."""

import logging

from fastapi import Depends, FastAPI, Header, HTTPException

from app.config import obter_config
from app.observability.logging import (
    configurar_logging,
)
from app.rag.ingest import executar_ingestao
from app.schemas import ChatRequest, ChatResponse
from app.portal.autenticacao import usuario_atual
from app.portal.banco import Usuario
from app.portal.rotas import executar_chat, rotas

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
app.include_router(rotas)


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
def chat(payload: ChatRequest, usuario: Usuario = Depends(usuario_atual)) -> ChatResponse:
    """Processa uma mensagem do usuario pela orquestracao multi-agente."""
    if payload.user_id != usuario.cliente_id:
        raise HTTPException(403, "O cliente informado nao pertence a sua sessao.")
    return executar_chat(payload.message, usuario)
