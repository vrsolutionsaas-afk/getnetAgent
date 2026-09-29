from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker

from app.portal import banco
from app.portal.autenticacao import verificar_senha
from scripts import preparar_portal


@pytest.fixture
def portal_vazio(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'portal.db').as_posix()}")
    fabrica = sessionmaker(engine, expire_on_commit=False)
    config = SimpleNamespace(portal_admin_email="admin@example.test", portal_admin_senha="Senha-teste-inicial")
    monkeypatch.setattr(banco, "fabrica_sessoes", lambda: fabrica)
    monkeypatch.setattr(preparar_portal, "fabrica_sessoes", lambda: fabrica)
    monkeypatch.setattr(preparar_portal, "obter_config", lambda: config)
    try:
        yield fabrica, config
    finally:
        engine.dispose()


def test_container_prepara_portal_antes_de_iniciar_api():
    dockerfile = Path(__file__).resolve().parents[1] / "Dockerfile"
    comando = next(linha for linha in dockerfile.read_text(encoding="utf-8").splitlines() if linha.startswith("CMD "))
    assert comando.startswith("CMD python -m scripts.preparar_portal && exec uvicorn app.main:app ")


def test_preparacao_cria_tabelas_limites_e_admin_no_banco_configurado(portal_vazio):
    fabrica, config = portal_vazio
    assert inspect(fabrica.kw["bind"]).get_table_names() == []

    preparar_portal.main()

    assert set(banco.Base.metadata.tables) <= set(inspect(fabrica.kw["bind"]).get_table_names())
    with fabrica() as sessao:
        assert sessao.get(banco.LimiteGlobal, 1) is not None
        admin = sessao.scalar(select(banco.Usuario).where(banco.Usuario.email == config.portal_admin_email))
        assert admin.perfil == "admin"
        assert admin.ativo
        assert verificar_senha(config.portal_admin_senha, admin.senha_hash)


def test_reinicio_preserva_admin_e_limites_apos_remover_senha_inicial(portal_vazio):
    fabrica, config = portal_vazio
    preparar_portal.main()
    with fabrica.begin() as sessao:
        admin = sessao.scalar(select(banco.Usuario))
        admin_id, senha_hash = admin.id, admin.senha_hash
        sessao.get(banco.LimiteGlobal, 1).limite_input = 123456

    config.portal_admin_senha = "Outra-senha-teste"
    preparar_portal.main()
    config.portal_admin_senha = ""
    preparar_portal.main()

    with fabrica() as sessao:
        usuarios = list(sessao.scalars(select(banco.Usuario)))
        assert len(usuarios) == 1
        assert (usuarios[0].id, usuarios[0].senha_hash) == (admin_id, senha_hash)
        assert sessao.get(banco.LimiteGlobal, 1).limite_input == 123456


def test_primeira_inicializacao_sem_credenciais_falha(portal_vazio):
    fabrica, config = portal_vazio
    config.portal_admin_email = ""
    config.portal_admin_senha = ""

    with pytest.raises(SystemExit, match="Defina PORTAL_ADMIN_EMAIL e PORTAL_ADMIN_SENHA"):
        preparar_portal.main()

    with fabrica() as sessao:
        assert sessao.scalar(select(banco.Usuario)) is None