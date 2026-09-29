"""Servidor isolado de pre-visualizacao. Nunca utilizado pela API de producao."""

import atexit
import importlib
import os
from datetime import timedelta
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import HTTPException

temporario = TemporaryDirectory(prefix="getnet-preview-")
os.environ["PORTAL_DATABASE_URL"] = f"sqlite:///{temporario.name}/portal.db"
os.environ["OPENAI_API_KEY"] = ""
os.environ["TAVILY_API_KEY"] = ""

from app.config import obter_config
from app.portal.autenticacao import hash_senha
from app.portal.banco import Chamada, Usuario, agora, fabrica_sessoes, inicializar
from app.portal.cotas import CotaExcedida, finalizar, reservar
from app.schemas import ChatResponse

obter_config.cache_clear()
fabrica_sessoes.cache_clear()
inicializar()
atexit.register(fabrica_sessoes().kw["bind"].dispose)
with fabrica_sessoes().begin() as sessao:
    for identificador, nome, perfil, conta in (
        ("admin-local", "Admin de demonstração", "admin", "cliente1988"),
        ("cliente-local", "Maria Oliveira", "cliente", "cliente1988"),
    ):
        sessao.add(Usuario(id=identificador, nome=nome, perfil=perfil,
                          email=f"{perfil}@getnet.local", senha_hash=hash_senha("Preview-local-2026"),
                          cliente_id=conta))

for indice in range(7):
    data = agora() - timedelta(days=indice)
    if data.month != agora().month:
        continue
    for etapa, modelo, entrada, saida in (
        ("roteamento", "gpt-4o-mini", 810 + indice * 117, 41 + indice * 3),
        ("geracao", "gpt-4o", 2710 + indice * 370, 325 + indice * 41),
    ):
        chamada_id = reservar("cliente-local", uuid4().hex, modelo, etapa, entrada + 100, saida + 100)
        finalizar(chamada_id, entrada, saida, cache=entrada // 3, duracao_ms=1800 + indice * 100)
        with fabrica_sessoes().begin() as sessao:
            sessao.get(Chamada, chamada_id).criado_em = data


def resposta_local(message: str, usuario: Usuario, historico: list | None = None) -> ChatResponse:
    try:
        chamada_id = reservar(usuario.id, uuid4().hex, "simulador-local", "geracao", 2000, 1024)
    except CotaExcedida as exc:
        raise HTTPException(429, str(exc)) from exc
    finalizar(chamada_id, 320, 85, cache=0, duracao_ms=240)
    return ChatResponse(response=(
        "**Prévia local com dados simulados.**\n\n"
        "Sua maquininha Get Smart está offline. Verifique a conexão Wi-Fi e reinicie o equipamento. "
        "Se o problema continuar, retorne com a mensagem exibida na tela."
    ), agent="support", route="conta_cliente", trace_id=uuid4().hex)


modulo_rotas = importlib.import_module("app.portal.rotas")
modulo_rotas.executar_chat = resposta_local

from app.main import app