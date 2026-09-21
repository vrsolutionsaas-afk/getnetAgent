"""Testes das ferramentas do Customer Support Agent (base mock, sem rede)."""

from app.tools import customer_tools


def test_liquidacao_cliente_existente():
    r = customer_tools.consultar_liquidacao_vendas("cliente1988")
    assert r["encontrado"] is True
    assert r["valor_liquido"] > 0
    assert "data_prevista_deposito" in r


def test_status_maquininha_offline():
    r = customer_tools.consultar_status_maquininha("cliente1988")
    assert r["encontrado"] is True
    assert r["status_conexao"] == "offline"
    assert r["modelo"] == "Get Smart"


def test_status_maquininha_online():
    r = customer_tools.consultar_status_maquininha("cliente2025")
    assert r["status_conexao"] == "online"


def test_antecipacao_disponivel():
    r = customer_tools.consultar_antecipacao("cliente1988")
    assert r["encontrado"] is True
    assert r["disponivel"] is True


def test_cliente_inexistente():
    r = customer_tools.consultar_liquidacao_vendas("naoexiste")
    assert r["encontrado"] is False
    assert r["motivo"] == "cliente_nao_encontrado"
