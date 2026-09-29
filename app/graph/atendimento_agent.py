"""Respostas de atendimento que nao precisam de modelo ou consulta externa."""

from app.graph.state import AgentState


RESPOSTAS = {
    "saudacao": (
        "Ola! Sou o assistente virtual da Getnet. "
        "Como posso ajudar com sua maquininha, suas vendas ou os servicos Getnet?"
    ),
    "encerramento": "Por nada! Se precisar de ajuda com a Getnet, estou por aqui.",
    "fora_escopo": (
        "Meu foco aqui e o atendimento Getnet. Posso ajudar com maquininhas, "
        "Pix, vendas e antecipacao de recebiveis. Qual e sua duvida?"
    ),
    "esclarecer": (
        "Pode detalhar o que voce precisa? E uma duvida sobre um produto Getnet "
        "ou sobre suas vendas e sua maquininha?"
    ),
}


def atendimento_agent(state: AgentState) -> AgentState:
    rota = state.get("route", "esclarecer")
    return {
        **state,
        "response": RESPOSTAS.get(rota, RESPOSTAS["esclarecer"]),
        "agent": "atendimento",
        "sources": [],
        "escalated": False,
        "trace": [*state.get("trace", []), f"atendimento -> {rota}"],
    }