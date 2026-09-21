"""Agente 3 - Customer Support: usa ferramentas para consultar dados do cliente.

O LLM decide QUAL ferramenta chamar, mas o user_id usado na execucao vem SEMPRE
do estado (nunca do LLM) - evita que o modelo invente identificadores de outros
clientes (guardrail deterministico de seguranca).
"""

import json
import logging

from langchain_core.tools import tool

from app.graph.llm import llm_geracao
from app.graph.state import AgentState
from app.tools import customer_tools

logger = logging.getLogger(__name__)


# As tools sao expostas ao LLM para SELECAO. O argumento user_id e ignorado na
# execucao real (substituido pelo user_id do estado).
@tool
def liquidacao_vendas(user_id: str) -> dict:
    """Consulta quando e quanto o cliente vai receber das vendas recentes (liquidacao)."""
    return customer_tools.consultar_liquidacao_vendas(user_id)


@tool
def status_maquininha(user_id: str) -> dict:
    """Consulta o status de conexao e diagnostico da maquininha do cliente."""
    return customer_tools.consultar_status_maquininha(user_id)


@tool
def antecipacao_recebiveis(user_id: str) -> dict:
    """Consulta a disponibilidade e valores de antecipacao de recebiveis do cliente."""
    return customer_tools.consultar_antecipacao(user_id)


TOOLS = [liquidacao_vendas, status_maquininha, antecipacao_recebiveis]
_EXECUTORES = {
    "liquidacao_vendas": customer_tools.consultar_liquidacao_vendas,
    "status_maquininha": customer_tools.consultar_status_maquininha,
    "antecipacao_recebiveis": customer_tools.consultar_antecipacao,
}

PROMPT_SUPPORT = """Voce e um atendente de suporte da Getnet. Use os dados do cliente \
fornecidos pelas ferramentas para responder de forma clara, cordial e objetiva. \
Formate valores em reais (R$) e datas de forma amigavel. Se a maquininha estiver \
offline, oriente passos praticos de reconexao. Nunca invente dados que nao estejam \
nos resultados das ferramentas."""


def support_agent(state: AgentState) -> AgentState:
    """No do grafo: consulta tools de dados do cliente e responde."""
    trace = state.get("trace", [])
    user_id = state["user_id"]
    mensagem = state["message"]

    llm_com_tools = llm_geracao().bind_tools(TOOLS)
    mensagens = [
        {"role": "system", "content": PROMPT_SUPPORT},
        {"role": "user", "content": mensagem},
    ]

    resposta_ia = llm_com_tools.invoke(mensagens)
    tool_calls = getattr(resposta_ia, "tool_calls", []) or []

    if not tool_calls:
        # LLM nao pediu ferramenta: responde direto (ou orienta)
        trace.append("support -> sem_tool")
        return {
            **state,
            "response": resposta_ia.content
            or "Pode me dar mais detalhes sobre o que precisa da sua conta Getnet?",
            "agent": "support",
            "sources": [],
            "trace": trace,
        }

    # Executa cada tool solicitada, SEMPRE com o user_id real do estado
    mensagens.append(resposta_ia)
    tools_usadas = []
    for chamada in tool_calls:
        nome = chamada["name"]
        executor = _EXECUTORES.get(nome)
        if not executor:
            continue
        resultado = executor(user_id)  # user_id do estado, nao o do LLM
        tools_usadas.append(nome)
        mensagens.append(
            {
                "role": "tool",
                "tool_call_id": chamada["id"],
                "content": json.dumps(resultado, ensure_ascii=False),
            }
        )

    trace.append(f"support -> tools: {', '.join(tools_usadas)}")
    logger.info(
        "support_tools",
        extra={
            "trace_id": state.get("trace_id"),
            "etapa": "support",
            "detalhe": ",".join(tools_usadas),
        },
    )

    resposta_final = llm_geracao().invoke(mensagens).content
    return {
        **state,
        "response": resposta_final,
        "agent": "support",
        "sources": [],
        "tool_results": {"tools": tools_usadas},
        "trace": trace,
    }
