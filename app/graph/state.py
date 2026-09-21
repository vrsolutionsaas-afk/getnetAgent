"""Estado compartilhado que trafega entre os nos do grafo LangGraph."""

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """Estado da orquestracao multi-agente.

    Campos preenchidos ao longo do fluxo: entrada -> router -> agente -> saida.
    """

    # Entrada
    message: str
    user_id: str

    # Decisao do Router Agent
    route: str  # "produto" | "conta_cliente" | "geral" | "escalar"

    # Contexto recuperado (RAG ou web) e resultados de tools
    contexto: str
    tool_results: dict

    # Saida
    response: str
    agent: str  # agente que produziu a resposta final
    sources: list[str]
    escalated: bool

    # Observabilidade
    trace_id: str
    trace: list[str]
