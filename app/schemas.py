"""Modelos Pydantic de entrada e saida da API."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload de entrada do endpoint /chat."""

    message: str = Field(..., description="Pergunta ou mensagem do usuario.")
    user_id: str = Field(..., description="Identificador do usuario/cliente.")


class ChatResponse(BaseModel):
    """Resposta estruturada do endpoint /chat."""

    response: str = Field(..., description="Resposta gerada para o usuario.")
    agent: str = Field(..., description="Agente que produziu a resposta final.")
    route: str = Field(..., description="Rota decidida pelo Router Agent.")
    sources: list[str] = Field(
        default_factory=list, description="Fontes usadas (URLs do RAG ou web search)."
    )
    escalated: bool = Field(
        default=False, description="Indica se houve transbordo para humano."
    )
    trace_id: str = Field(..., description="Identificador do trace para observabilidade.")
    trace: list[str] = Field(
        default_factory=list, description="Passos percorridos na orquestracao."
    )
