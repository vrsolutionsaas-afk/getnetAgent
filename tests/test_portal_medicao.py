from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI
import pytest

from app.portal.medicao import ContextoConsumo, ModeloMedido, contexto_consumo


def test_mede_chamada_com_tools_e_usage_do_provedor(monkeypatch):
    import app.portal.medicao as medicao
    reservas, fechamentos = [], []
    monkeypatch.setattr(medicao, "reservar", lambda *args: reservas.append(args) or "id")
    monkeypatch.setattr(medicao, "finalizar", lambda *args, **kwargs: fechamentos.append((args, kwargs)))
    monkeypatch.setattr(ChatOpenAI, "_generate", lambda *args, **kwargs: ChatResult(
        generations=[ChatGeneration(message=AIMessage(content="Resposta"))],
        llm_output={"token_usage": {"prompt_tokens": 30, "completion_tokens": 4,
                                   "prompt_tokens_details": {"cached_tokens": 10}}}))
    modelo = ModeloMedido(api_key="teste", max_tokens=256)
    token = contexto_consumo.set(ContextoConsumo("cliente", "trace"))
    try:
        modelo.bind_tools([{"type": "function", "function": {"name": "consulta", "description": "Consulta", "parameters": {"type": "object", "properties": {}}}}]).invoke([HumanMessage(content="Oi")])
    finally:
        contexto_consumo.reset(token)
    assert reservas[0][:2] == ("cliente", "trace")
    assert reservas[0][-1] == 256
    assert fechamentos[0][0] == ("id", 30, 4)
    assert fechamentos[0][1]["cache"] == 10


def test_cota_insuficiente_nao_chama_provedor(monkeypatch):
    import app.portal.medicao as medicao
    from app.portal.cotas import CotaExcedida
    def bloquear(*args):
        raise CotaExcedida("Sem saldo")
    monkeypatch.setattr(medicao, "reservar", bloquear)
    monkeypatch.setattr(ChatOpenAI, "_generate", lambda *args, **kwargs: pytest.fail("Provedor nao deveria ser chamado"))
    modelo = ModeloMedido(api_key="teste", max_tokens=256)
    token = contexto_consumo.set(ContextoConsumo("cliente", "trace"))
    try:
        with pytest.raises(CotaExcedida):
            modelo.invoke([HumanMessage(content="Oi")])
    finally:
        contexto_consumo.reset(token)