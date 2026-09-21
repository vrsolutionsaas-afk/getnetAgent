"""Agente 1 - Router: classifica a mensagem e decide qual agente deve atender."""

import logging

from pydantic import BaseModel, Field

from app.graph.llm import llm_roteamento
from app.graph.state import AgentState

logger = logging.getLogger(__name__)

ROTAS_VALIDAS = {"produto", "conta_cliente", "geral", "escalar"}

PROMPT_ROTEAMENTO = """Voce e o roteador de um sistema de atendimento da Getnet \
(adquirente de pagamentos: maquininhas de cartao, Pix, antecipacao de recebiveis, \
link de pagamento, crediario).

Classifique a mensagem do cliente em UMA das rotas:

- "produto": duvidas sobre produtos/servicos da Getnet (diferenca entre maquininhas, \
como funciona Pix, antecipacao, link de pagamento, crediario, taxas, prazos gerais). \
NAO depende de dados especificos da conta do cliente.

- "conta_cliente": precisa consultar dados DO cliente para responder (quando cai o \
dinheiro das MINHAS vendas, status da MINHA maquininha, MINHA antecipacao disponivel, \
problemas tecnicos com o MEU equipamento).

- "geral": pergunta fora do dominio Getnet que exige informacao externa atual \
(previsao do tempo, cotacao de moeda, noticias).

- "escalar": conteudo ofensivo, pedido sensivel/inseguro, reclamacao grave, fraude, \
ou algo que o sistema nao consegue resolver com seguranca.

Responda apenas com a rota."""


class DecisaoRota(BaseModel):
    """Saida estruturada do roteador."""

    rota: str = Field(description="Uma das rotas: produto, conta_cliente, geral, escalar")


def router_agent(state: AgentState) -> AgentState:
    """No do grafo: decide a rota da mensagem."""
    mensagem = state["message"]
    llm = llm_roteamento().with_structured_output(DecisaoRota)

    try:
        decisao: DecisaoRota = llm.invoke(
            [
                {"role": "system", "content": PROMPT_ROTEAMENTO},
                {"role": "user", "content": mensagem},
            ]
        )
        rota = decisao.rota.strip().lower()
    except Exception as exc:  # noqa: BLE001 - falha de roteamento cai no fallback
        logger.warning("Falha no roteamento, usando 'produto' como fallback: %s", exc)
        rota = "produto"

    if rota not in ROTAS_VALIDAS:
        rota = "produto"

    trace = state.get("trace", [])
    trace.append(f"router -> {rota}")
    logger.info(
        "roteamento",
        extra={"trace_id": state.get("trace_id"), "etapa": "router", "detalhe": rota},
    )
    return {**state, "route": rota, "trace": trace}
