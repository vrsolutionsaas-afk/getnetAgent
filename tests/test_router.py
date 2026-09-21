"""Testes da logica de roteamento do grafo (sem chamar LLM)."""

from app.graph.builder import _rota_pos_guardrail, _rota_pos_router
from app.graph.router_agent import ROTAS_VALIDAS


def test_rotas_validas_definidas():
    assert ROTAS_VALIDAS == {"produto", "conta_cliente", "geral", "escalar"}


def test_guardrail_bloqueado_vai_para_escalation():
    assert _rota_pos_guardrail({"route": "escalar"}) == "escalation"


def test_guardrail_ok_vai_para_router():
    assert _rota_pos_guardrail({}) == "router"


def test_conta_cliente_vai_para_support():
    assert _rota_pos_router({"route": "conta_cliente"}) == "support"


def test_produto_vai_para_knowledge():
    assert _rota_pos_router({"route": "produto"}) == "knowledge"


def test_geral_vai_para_knowledge():
    assert _rota_pos_router({"route": "geral"}) == "knowledge"


def test_escalar_vai_para_escalation():
    assert _rota_pos_router({"route": "escalar"}) == "escalation"
