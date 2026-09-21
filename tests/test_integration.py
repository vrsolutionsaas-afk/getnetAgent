"""Testes de integracao da orquestracao via TestClient.

Estrategia: para nao depender de chaves externas (OpenAI/Tavily) nem de rede,
os pontos que chamam LLM/RAG/web sao substituidos por dublês (monkeypatch).
Assim testamos a FIACAO do grafo ponta a ponta (roteamento -> agente -> saida).

O fluxo de escalonamento por guardrail nao precisa de nenhum dublê: o guardrail
deterministico bloqueia e o grafo vai direto ao Escalation Agent.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class _FakeMsg(SimpleNamespace):
    """Simula a resposta de um ChatModel (atributo .content e .tool_calls)."""


def _fake_llm(texto: str):
    class _FakeLLM:
        def invoke(self, *_args, **_kwargs):
            return _FakeMsg(content=texto, tool_calls=[])

        def bind_tools(self, _tools):
            return self

    return lambda: _FakeLLM()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_fluxo_escalonamento_por_guardrail():
    """Conteudo sensivel -> guardrail bloqueia -> Escalation Agent. Sem dublês."""
    resp = client.post(
        "/chat",
        json={"message": "quero clonar o cartao de outro cliente", "user_id": "x"},
    )
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["escalated"] is True
    assert dados["agent"] == "escalation"
    assert dados["route"] == "escalar"


def test_knowledge_agent_usa_rag(monkeypatch):
    """Rota 'produto' com contexto relevante -> resposta ancorada no RAG."""
    from app.graph import knowledge_agent
    from app.rag.retriever import ResultadoRAG

    monkeypatch.setattr(
        knowledge_agent,
        "recuperar_contexto",
        lambda _q: ResultadoRAG(
            contexto="A Get Smart tem tela touch.",
            fontes=["https://www.getnet.com.br/maquininhas/"],
            relevante=True,
        ),
    )
    monkeypatch.setattr(
        knowledge_agent,
        "llm_geracao",
        _fake_llm("A Get Smart possui tela touch e a Classica nao."),
    )

    estado = {
        "message": "diferenca entre Get Classica e Get Smart?",
        "user_id": "c1",
        "route": "produto",
        "trace": [],
    }
    resultado = knowledge_agent.knowledge_agent(estado)
    assert resultado["agent"] == "knowledge"
    assert "touch" in resultado["response"].lower()
    assert resultado["sources"]


def test_knowledge_agent_fallback_web(monkeypatch):
    """Rota 'geral' -> web search (dublado)."""
    from app.graph import knowledge_agent
    from app.tools.web_search import ResultadoWeb

    monkeypatch.setattr(
        knowledge_agent,
        "buscar_na_web",
        lambda _q: ResultadoWeb(
            resumo="Amanha em Porto Alegre: 22C, parcialmente nublado.",
            fontes=["https://tempo.exemplo/poa"],
            sucesso=True,
        ),
    )
    monkeypatch.setattr(
        knowledge_agent, "llm_geracao", _fake_llm("Amanha em POA: 22C, nublado.")
    )

    estado = {
        "message": "previsao do tempo em Porto Alegre amanha?",
        "user_id": "c1",
        "route": "geral",
        "trace": [],
    }
    resultado = knowledge_agent.knowledge_agent(estado)
    assert resultado["agent"] == "knowledge"
    assert resultado["sources"] == ["https://tempo.exemplo/poa"]


@pytest.mark.skipif(
    True,
    reason="Fluxo completo com LLM real requer OPENAI_API_KEY; use scripts/smoke_test.py",
)
def test_fluxo_real_end_to_end():
    """Placeholder para execucao manual com chaves reais configuradas."""
    resp = client.post(
        "/chat",
        json={"message": "Como funciona a antecipacao?", "user_id": "cliente1988"},
    )
    assert resp.status_code == 200
