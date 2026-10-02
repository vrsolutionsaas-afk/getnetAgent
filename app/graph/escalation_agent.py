"""Sinaliza casos para atendimento humano, sem simular transferencia ou ticket."""

import logging

from app.graph.state import AgentState

logger = logging.getLogger(__name__)

MENSAGEM_TRANSBORDO = (
    "Esse caso precisa de atendimento humano para ser tratado com seguranca. "
    "Este portal demonstrativo nao transfere conversas nem abre protocolos. "
    "Procure os canais oficiais de atendimento no site da Getnet. "
    "Nao envie senhas, codigos de seguranca ou dados completos de cartao aqui."
)

RESPOSTAS_GUARDRAIL = {
    "instrucao_maliciosa": (
        "Nao posso alterar as regras de seguranca nem revelar instrucoes internas. "
        "Posso ajudar com produtos Getnet ou com as consultas permitidas da sua conta."
    ),
    "dados_pessoais": (
        "Por seguranca, nao compartilhe CPF, numeros completos de cartao ou dados de terceiros. "
        "Descreva sua duvida sem esses dados; as consultas usam apenas o cliente da sua sessao."
    ),
    "conteudo_sensivel": (
        "Nao posso ajudar com esse pedido. Nunca compartilhe senhas, tokens ou codigos de "
        "seguranca. Posso ajudar com sua maquininha, suas vendas, antecipacao ou produtos Getnet."
    ),
    "mensagem_vazia": "Escreva sua duvida sobre a Getnet para eu poder ajudar.",
    "mensagem_longa": "Resuma sua duvida em ate 2.500 caracteres, sem dados sensiveis.",
}


def escalation_agent(state: AgentState) -> AgentState:
    """No do grafo: recusa bloqueios de seguranca ou orienta atendimento humano."""
    trace = state.get("trace", [])
    recusa = RESPOSTAS_GUARDRAIL.get(state.get("guardrail_motivo", ""))
    trace.append("escalation -> recusa" if recusa else "escalation -> orientacao_sem_transferencia")

    logger.info(
        "recusa_guardrail" if recusa else "orientacao_humana",
        extra={
            "trace_id": state.get("trace_id"),
            "etapa": "escalation",
            "detalhe": state.get("user_id"),
        },
    )
    return {
        **state,
        "response": recusa or MENSAGEM_TRANSBORDO,
        "agent": "escalation",
        "sources": [],
        "escalated": recusa is None,
        "trace": trace,
    }
