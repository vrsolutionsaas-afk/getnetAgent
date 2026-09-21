"""Montagem do grafo de orquestracao multi-agente (LangGraph).

Fluxo:
    guardrail_entrada -> (bloqueado?) -> escalation
                      -> router -> (rota) -> knowledge | support | escalation
    <agente> -> finalizar (guardrail de saida) -> FIM
"""

import logging
from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.graph.escalation_agent import escalation_agent
from app.graph.knowledge_agent import knowledge_agent
from app.graph.router_agent import router_agent
from app.graph.state import AgentState
from app.graph.support_agent import support_agent
from app.guardrails.input_guard import checar_entrada
from app.guardrails.output_guard import sanear_saida

logger = logging.getLogger(__name__)


def _no_guardrail_entrada(state: AgentState) -> AgentState:
    """No inicial: aplica o guardrail de entrada."""
    resultado = checar_entrada(state["message"])
    trace = state.get("trace", [])
    if resultado.bloqueado:
        trace.append(f"guardrail_entrada -> bloqueado ({resultado.motivo})")
        return {**state, "route": "escalar", "trace": trace}
    trace.append("guardrail_entrada -> ok")
    return {**state, "trace": trace}


def _no_finalizar(state: AgentState) -> AgentState:
    """No final: aplica o guardrail de saida na resposta."""
    resposta = sanear_saida(state.get("response", ""))
    trace = state.get("trace", [])
    trace.append("finalizar -> guardrail_saida")
    return {**state, "response": resposta, "trace": trace}


def _rota_pos_guardrail(state: AgentState) -> str:
    """Se o guardrail bloqueou, vai direto para escalation; senao, roteia."""
    return "escalation" if state.get("route") == "escalar" else "router"


def _rota_pos_router(state: AgentState) -> str:
    """Mapeia a decisao do router para o proximo no."""
    rota = state.get("route")
    if rota == "conta_cliente":
        return "support"
    if rota == "escalar":
        return "escalation"
    # "produto" e "geral" sao atendidos pelo knowledge agent
    return "knowledge"


@lru_cache
def construir_grafo():
    """Constroi e compila o grafo LangGraph (cacheado)."""
    grafo = StateGraph(AgentState)

    grafo.add_node("guardrail_entrada", _no_guardrail_entrada)
    grafo.add_node("router", router_agent)
    grafo.add_node("knowledge", knowledge_agent)
    grafo.add_node("support", support_agent)
    grafo.add_node("escalation", escalation_agent)
    grafo.add_node("finalizar", _no_finalizar)

    grafo.set_entry_point("guardrail_entrada")

    grafo.add_conditional_edges(
        "guardrail_entrada",
        _rota_pos_guardrail,
        {"router": "router", "escalation": "escalation"},
    )
    grafo.add_conditional_edges(
        "router",
        _rota_pos_router,
        {
            "knowledge": "knowledge",
            "support": "support",
            "escalation": "escalation",
        },
    )

    grafo.add_edge("knowledge", "finalizar")
    grafo.add_edge("support", "finalizar")
    grafo.add_edge("escalation", "finalizar")
    grafo.add_edge("finalizar", END)

    return grafo.compile()
