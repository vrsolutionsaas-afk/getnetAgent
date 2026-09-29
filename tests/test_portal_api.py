import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.portal.autenticacao import hash_senha, nova_sessao
from app.portal.banco import Conversa, Usuario, fabrica_sessoes
from app.portal.cotas import finalizar, reservar
from app.portal.rotas import rotas
from tests.test_portal_cotas import banco_portal


@pytest.fixture
def cliente_portal(banco_portal):
    with fabrica_sessoes().begin() as sessao:
        usuario = sessao.get(Usuario, "teste")
        usuario.senha_hash = hash_senha("Senha-segura-teste")
    app = FastAPI()
    app.include_router(rotas)
    return TestClient(app)


def test_login_sessao_cotas_e_logout(cliente_portal):
    resposta = cliente_portal.post("/portal/login", json={"email": "cliente@example.test", "senha": "Senha-segura-teste"})
    assert resposta.status_code == 200
    headers = {"Authorization": f"Bearer {resposta.json()['token']}"}
    assert cliente_portal.get("/portal/sessao", headers=headers).json()["consumo"]["limite_input"] == 100
    assert cliente_portal.get("/portal/admin/usuarios", headers=headers).status_code == 403
    assert cliente_portal.get("/portal/conversas/inexistente", headers=headers).status_code == 404
    assert cliente_portal.post("/portal/logout", headers=headers).status_code == 200
    assert cliente_portal.get("/portal/sessao", headers=headers).status_code == 401


def test_sem_login_nao_acessa_chat(cliente_portal):
    assert cliente_portal.post("/portal/mensagens", json={"message": "Oi", "conversa_id": "outra"}).status_code == 401


def test_senha_incorreta_e_tentativas_limitadas(cliente_portal):
    for indice in range(9):
        resposta = cliente_portal.post("/portal/login", json={"email": "cliente@example.test", "senha": "errada"})
    assert resposta.status_code == 429


def test_admin_clientes_cotas_e_painel(cliente_portal):
    with fabrica_sessoes().begin() as sessao:
        sessao.get(Usuario, "teste").perfil = "admin"
    headers = {"Authorization": f"Bearer {nova_sessao('teste')}"}
    chamada = reservar("teste", "trace", "modelo", "geracao", 50, 25)
    finalizar(chamada, 20, 10, cache=5)
    for dias in (7, 30, 90):
        painel = cliente_portal.get(f"/portal/admin/painel?dias={dias}", headers=headers)
        assert painel.status_code == 200, painel.text
        assert (painel.json()["input"], painel.json()["output"], painel.json()["cache"]) == (20, 10, 5)
    assert cliente_portal.get("/portal/admin/painel?dias=8", headers=headers).status_code == 422
    novo = cliente_portal.post("/portal/admin/usuarios", headers=headers, json={
        "nome": "Outra pessoa", "email": "outra@example.test", "senha": "Outra-senha-segura",
        "cliente_id": "cliente2025", "limite_input": 80000, "limite_output": 20000,
    })
    assert novo.status_code == 200, novo.text
    assert "senha_hash" not in novo.json()
    usuario_id = novo.json()["id"]
    cliente_headers = {"Authorization": f"Bearer {nova_sessao(usuario_id)}"}
    assert cliente_portal.patch(f"/portal/admin/usuarios/{usuario_id}", headers=headers, json={
        "ativo": False, "limite_input": 1000, "limite_output": 500,
    }).status_code == 200
    assert cliente_portal.get("/portal/sessao", headers=cliente_headers).status_code == 401
    assert cliente_portal.put("/portal/admin/cotas", headers=headers, json={
        "limite_input": 200, "limite_output": 100,
    }).status_code == 200
    assert cliente_portal.get("/portal/admin/painel", headers=headers).json()["cotas"]["limite_input"] == 200


def test_conversa_isolada_e_historico(cliente_portal, monkeypatch):
    import importlib
    from app.schemas import ChatResponse
    modulo = importlib.import_module("app.portal.rotas")
    headers = {"Authorization": f"Bearer {nova_sessao('teste')}"}
    with fabrica_sessoes().begin() as sessao:
        sessao.add(Usuario(id="outra", nome="Outra", email="outra@example.test", senha_hash="x", cliente_id="cliente2025"))
        sessao.add(Conversa(id="privada", usuario_id="outra", titulo="Privada"))
    assert cliente_portal.get("/portal/conversas/privada", headers=headers).status_code == 404
    assert cliente_portal.post("/portal/mensagens", headers=headers, json={"message": "Oi", "conversa_id": "privada"}).status_code == 404
    conversa = cliente_portal.post("/portal/conversas", headers=headers).json()
    chamadas = []
    def responder(message, usuario, historico):
        chamadas.append((usuario.cliente_id, historico))
        return ChatResponse(response="Resposta", agent="support", route="conta_cliente", trace_id="trace")
    monkeypatch.setattr(modulo, "executar_chat", responder)
    for texto in ("Minha conta", "E a maquininha?"):
        resposta = cliente_portal.post("/portal/mensagens", headers=headers, json={"message": texto, "conversa_id": conversa["id"]})
        assert resposta.status_code == 200, resposta.text
    assert chamadas[1] == ("cliente1988", [{"role": "user", "content": "Minha conta"}, {"role": "assistant", "content": "Resposta"}])
    assert len(cliente_portal.get(f"/portal/conversas/{conversa['id']}", headers=headers).json()) == 4


def test_chat_original_exige_identidade_da_sessao(cliente_portal):
    from app.main import app
    cliente = TestClient(app)
    payload = {"message": "Oi", "user_id": "cliente2025"}
    assert cliente.post("/chat", json=payload).status_code == 401
    headers = {"Authorization": f"Bearer {nova_sessao('teste')}"}
    assert cliente.post("/chat", json=payload, headers=headers).status_code == 403