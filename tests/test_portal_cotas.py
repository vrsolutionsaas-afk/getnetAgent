import pytest

from app.config import obter_config
from app.portal.banco import Consumo, LimiteGlobal, Usuario, fabrica_sessoes, inicializar, agora
from app.portal.cotas import CotaExcedida, finalizar, reservar


@pytest.fixture
def banco_portal(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTAL_DATABASE_URL", f"sqlite:///{tmp_path / 'portal.db'}")
    obter_config.cache_clear()
    fabrica_sessoes.cache_clear()
    inicializar()
    with fabrica_sessoes().begin() as sessao:
        sessao.add(Usuario(id="teste", nome="Cliente", email="cliente@example.test",
                          senha_hash="nao-utilizada", cliente_id="cliente1988",
                          limite_input=100, limite_output=50))
    yield
    fabrica_sessoes().kw["bind"].dispose()
    fabrica_sessoes.cache_clear()
    obter_config.cache_clear()


def test_preparar_admin_idempotente(banco_portal, monkeypatch):
    from scripts.preparar_portal import main
    from sqlalchemy import select
    from app.portal.autenticacao import verificar_senha
    monkeypatch.setenv("PORTAL_ADMIN_EMAIL", "admin@example.test")
    monkeypatch.setenv("PORTAL_ADMIN_SENHA", "Senha-segura-do-admin")
    obter_config.cache_clear()
    main()
    main()
    with fabrica_sessoes()() as sessao:
        usuario = sessao.scalar(select(Usuario).where(Usuario.email == "admin@example.test"))
        assert usuario.perfil == "admin"
        assert verificar_senha("Senha-segura-do-admin", usuario.senha_hash)


def test_reserva_impede_reutilizar_saldo(banco_portal):
    reservar("teste", "trace", "modelo", "router", 80, 40)
    with pytest.raises(CotaExcedida):
        reservar("teste", "trace2", "modelo", "router", 30, 20)


def test_contabiliza_uso_e_libera_excedente_uma_vez(banco_portal):
    chamada = reservar("teste", "trace", "modelo", "router", 80, 40)
    finalizar(chamada, 20, 10, cache=5)
    finalizar(chamada, 20, 10)
    with fabrica_sessoes()() as sessao:
        consumo = sessao.get(Consumo, ("teste", agora().strftime("%Y-%m")))
        assert (consumo.input, consumo.output, consumo.reservado_input) == (20, 10, 0)
    reservar("teste", "trace2", "modelo", "router", 80, 40)


def test_falha_sem_usage_mantem_cobranca_conservadora(banco_portal):
    chamada = reservar("teste", "trace", "modelo", "router", 100, 50)
    finalizar(chamada, None, None)
    with pytest.raises(CotaExcedida):
        reservar("teste", "trace2", "modelo", "router", 1, 1)


@pytest.mark.parametrize("entrada,saida", [(101, 0), (0, 51)])
def test_limites_independentes(banco_portal, entrada, saida):
    with pytest.raises(CotaExcedida):
        reservar("teste", "trace", "modelo", "router", entrada, saida)


def test_cota_global_bloqueia_entre_usuarios(banco_portal):
    with fabrica_sessoes().begin() as sessao:
        sessao.get(LimiteGlobal, 1).limite_input = 100
        sessao.add(Usuario(id="outro", nome="Outro", email="outro@example.test", senha_hash="x", cliente_id="cliente2025"))
    reservar("teste", "trace", "modelo", "router", 80, 10)
    with pytest.raises(CotaExcedida):
        reservar("outro", "trace2", "modelo", "router", 21, 10)