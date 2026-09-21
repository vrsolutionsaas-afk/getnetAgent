"""Agente 4 (bonus) - Human Escalation: transbordo para atendente humano.

Acionado quando o Router classifica como "escalar" ou quando um guardrail
detecta conteudo inseguro/sensivel/fora de escopo. Registra o handoff e
retorna uma mensagem cordial informando o encaminhamento.
"""

import logging

from app.graph.state import AgentState

logger = logging.getLogger(__name__)

MENSAGEM_TRANSBORDO = (
    "Entendo seu pedido. Para te atender com seguranca e da melhor forma, vou "
    "encaminhar essa conversa para um de nossos atendentes humanos, que dara "
    "continuidade em instantes. Obrigado pela compreensao."
)


def escalation_agent(state: AgentState) -> AgentState:
    """No do grafo: efetiva o transbordo para humano."""
    trace = state.get("trace", [])
    trace.append("escalation -> handoff_humano")

    logger.info(
        "handoff_humano",
        extra={
            "trace_id": state.get("trace_id"),
            "etapa": "escalation",
            "detalhe": state.get("user_id"),
        },
    )
    return {
        **state,
        "response": MENSAGEM_TRANSBORDO,
        "agent": "escalation",
        "sources": [],
        "escalated": True,
        "trace": trace,
    }
