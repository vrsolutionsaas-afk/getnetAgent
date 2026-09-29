import logging
import secrets
from datetime import timedelta, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import String, cast, delete, func, select

from app.graph.builder import construir_grafo
from app.portal.autenticacao import administrador, hash_senha, hash_token, nova_sessao, usuario_atual, verificar_senha
from app.portal.banco import Chamada, Consumo, Conversa, LimiteGlobal, Mensagem, Sessao, TentativaLogin, Usuario, agora, fabrica_sessoes
from app.portal.cotas import CotaExcedida
from app.portal.medicao import ContextoConsumo, contexto_consumo
from app.schemas import ChatResponse

rotas = APIRouter(prefix="/portal", tags=["Portal"])
logger = logging.getLogger(__name__)
HASH_FICTICIO = hash_senha(secrets.token_urlsafe(32))


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    senha: str = Field(min_length=1, max_length=128)


class Limites(BaseModel):
    limite_input: int = Field(ge=0, le=2000000000)
    limite_output: int = Field(ge=0, le=2000000000)


class NovoUsuario(Limites):
    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    senha: str = Field(min_length=12, max_length=128)
    cliente_id: Literal["cliente1988", "cliente2025"] = "cliente1988"

    @field_validator("email")
    @classmethod
    def validar_email(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if "@" not in valor or "." not in valor.split("@")[-1]:
            raise ValueError("Email invalido")
        return valor


class EditarUsuario(Limites):
    ativo: bool


class NovaMensagem(BaseModel):
    message: str = Field(min_length=1, max_length=2500)
    conversa_id: str = Field(max_length=64)


def dados_usuario(usuario: Usuario) -> dict:
    return {"id": usuario.id, "nome": usuario.nome, "email": usuario.email,
            "perfil": usuario.perfil, "ativo": usuario.ativo,
            "cliente_id": usuario.cliente_id,
            "limite_input": usuario.limite_input, "limite_output": usuario.limite_output}


def dados_consumo(sessao, escopo: str, limites) -> dict:
    mes = agora().strftime("%Y-%m")
    consumo = sessao.get(Consumo, (escopo, mes))
    return {"mes": mes, "input": consumo.input if consumo else 0,
            "output": consumo.output if consumo else 0,
            "reservado_input": consumo.reservado_input if consumo else 0,
            "reservado_output": consumo.reservado_output if consumo else 0,
            "limite_input": limites.limite_input, "limite_output": limites.limite_output}


@rotas.post("/login")
def entrar(payload: Login, request: Request):
    email = payload.email.strip().lower()
    limitado = False
    with fabrica_sessoes().begin() as sessao:
        sessao.scalar(select(LimiteGlobal).where(LimiteGlobal.id == 1).with_for_update())
        for chave, maximo in ((hash_token(email), 8), (hash_token(request.client.host if request.client else "local"), 100)):
            tentativa = sessao.get(TentativaLogin, chave)
            if tentativa is None:
                tentativa = TentativaLogin(chave=chave, quantidade=0, inicio=agora())
                sessao.add(tentativa)
            if tentativa.inicio.replace(tzinfo=timezone.utc) < agora() - timedelta(minutes=15):
                tentativa.quantidade, tentativa.inicio = 0, agora()
            limitado = limitado or tentativa.quantidade >= maximo
            tentativa.quantidade += 1
        usuario = sessao.scalar(select(Usuario).where(Usuario.email == email))
    if limitado:
        raise HTTPException(429, "Muitas tentativas. Aguarde 15 minutos.")
    valido = verificar_senha(payload.senha, usuario.senha_hash if usuario else HASH_FICTICIO)
    if not usuario or not valido or not usuario.ativo:
        raise HTTPException(401, "Email ou senha invalidos.")
    return {"token": nova_sessao(usuario.id), "usuario": dados_usuario(usuario)}


@rotas.post("/logout")
def sair(request: Request, usuario: Usuario = Depends(usuario_atual)):
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    with fabrica_sessoes().begin() as sessao:
        sessao.execute(delete(Sessao).where(Sessao.token_hash == hash_token(token)))
    return {"ok": True}


@rotas.get("/sessao")
def minha_sessao(usuario: Usuario = Depends(usuario_atual)):
    with fabrica_sessoes()() as sessao:
        return {"usuario": dados_usuario(usuario), "consumo": dados_consumo(sessao, usuario.id, usuario)}


@rotas.get("/conversas")
def listar_conversas(usuario: Usuario = Depends(usuario_atual)):
    with fabrica_sessoes()() as sessao:
        conversas = sessao.scalars(select(Conversa).where(Conversa.usuario_id == usuario.id)
                                  .order_by(Conversa.criado_em.desc()).limit(100))
        return [{"id": conversa.id, "titulo": conversa.titulo, "criado_em": conversa.criado_em} for conversa in conversas]


@rotas.post("/conversas")
def criar_conversa(usuario: Usuario = Depends(usuario_atual)):
    with fabrica_sessoes().begin() as sessao:
        conversa = Conversa(id=uuid4().hex, usuario_id=usuario.id, titulo="Nova conversa")
        sessao.add(conversa)
    return {"id": conversa.id, "titulo": conversa.titulo}


def obter_conversa(sessao, conversa_id: str, usuario_id: str) -> Conversa:
    conversa = sessao.scalar(select(Conversa).where(Conversa.id == conversa_id,
                                                   Conversa.usuario_id == usuario_id).with_for_update())
    if conversa is None:
        raise HTTPException(404, "Conversa nao encontrada.")
    return conversa


@rotas.get("/conversas/{conversa_id}")
def listar_mensagens(conversa_id: str, usuario: Usuario = Depends(usuario_atual)):
    with fabrica_sessoes()() as sessao:
        obter_conversa(sessao, conversa_id, usuario.id)
        mensagens = sessao.scalars(select(Mensagem).where(Mensagem.conversa_id == conversa_id).order_by(Mensagem.id))
        return [{"id": mensagem.id, "papel": mensagem.papel, "texto": mensagem.texto,
                 "fontes": mensagem.fontes, "agente": mensagem.agente} for mensagem in mensagens]


def executar_chat(message: str, usuario: Usuario, historico: list | None = None) -> ChatResponse:
    if not message.strip() or len(message) > 2500:
        raise HTTPException(422, "A mensagem deve conter de 1 a 2500 caracteres.")
    trace_id = uuid4().hex
    token = contexto_consumo.set(ContextoConsumo(usuario.id, trace_id))
    try:
        estado = construir_grafo().invoke({"message": message, "user_id": usuario.cliente_id,
                                          "trace_id": trace_id, "trace": [], "sources": [],
                                          "escalated": False, "historico": historico or []})
        return ChatResponse(response=estado.get("response", ""), agent=estado.get("agent", ""),
                            route=estado.get("route", ""), sources=estado.get("sources", []),
                            escalated=estado.get("escalated", False), trace_id=trace_id,
                            trace=estado.get("trace", []))
    except CotaExcedida as exc:
        raise HTTPException(429, str(exc)) from exc
    except Exception as exc:
        logger.error("Falha no chat", extra={"trace_id": trace_id, "etapa": "chat", "detalhe": type(exc).__name__})
        raise HTTPException(502, "Atendimento indisponivel no momento. Tente novamente.") from exc
    finally:
        contexto_consumo.reset(token)


@rotas.post("/mensagens")
def enviar_mensagem(payload: NovaMensagem, usuario: Usuario = Depends(usuario_atual)):
    with fabrica_sessoes().begin() as sessao:
        conversa = obter_conversa(sessao, payload.conversa_id, usuario.id)
        if conversa.processando_em and conversa.processando_em.replace(tzinfo=timezone.utc) > agora() - timedelta(minutes=5):
            raise HTTPException(409, "Aguarde a resposta da mensagem anterior.")
        conversa.processando_em = agora()
        anteriores = list(sessao.scalars(select(Mensagem).where(Mensagem.conversa_id == conversa.id)
                                         .order_by(Mensagem.id.desc()).limit(12)))
        historico = [{"role": mensagem.papel, "content": mensagem.texto[:1500]} for mensagem in reversed(anteriores)]
    try:
        resposta = executar_chat(payload.message, usuario, historico)
        with fabrica_sessoes().begin() as sessao:
            conversa = obter_conversa(sessao, payload.conversa_id, usuario.id)
            if not anteriores:
                conversa.titulo = payload.message[:80]
            sessao.add(Mensagem(conversa_id=conversa.id, papel="user", texto=payload.message))
            sessao.add(Mensagem(conversa_id=conversa.id, papel="assistant", texto=resposta.response,
                                fontes=resposta.sources, agente=resposta.agent))
        return resposta
    finally:
        with fabrica_sessoes().begin() as sessao:
            conversa = obter_conversa(sessao, payload.conversa_id, usuario.id)
            conversa.processando_em = None


@rotas.get("/admin/usuarios", dependencies=[Depends(administrador)])
def listar_usuarios():
    with fabrica_sessoes()() as sessao:
        return [{**dados_usuario(usuario), "consumo": dados_consumo(sessao, usuario.id, usuario)}
                for usuario in sessao.scalars(select(Usuario).order_by(Usuario.nome))]


@rotas.post("/admin/usuarios", dependencies=[Depends(administrador)])
def criar_usuario(payload: NovoUsuario):
    from sqlalchemy.exc import IntegrityError
    try:
        with fabrica_sessoes().begin() as sessao:
            usuario = Usuario(id=uuid4().hex, nome=payload.nome.strip(), email=payload.email,
                              senha_hash=hash_senha(payload.senha), cliente_id=payload.cliente_id,
                              limite_input=payload.limite_input, limite_output=payload.limite_output)
            sessao.add(usuario)
        return dados_usuario(usuario)
    except IntegrityError as exc:
        raise HTTPException(409, "Email ja cadastrado.") from exc


@rotas.patch("/admin/usuarios/{usuario_id}")
def editar_usuario(usuario_id: str, payload: EditarUsuario, admin: Usuario = Depends(administrador)):
    with fabrica_sessoes().begin() as sessao:
        sessao.scalar(select(LimiteGlobal).where(LimiteGlobal.id == 1).with_for_update())
        usuario = sessao.get(Usuario, usuario_id)
        if not usuario:
            raise HTTPException(404, "Usuario nao encontrado.")
        if usuario.id == admin.id and not payload.ativo:
            raise HTTPException(422, "Voce nao pode bloquear seu proprio acesso.")
        usuario.limite_input, usuario.limite_output, usuario.ativo = payload.limite_input, payload.limite_output, payload.ativo
        if not payload.ativo:
            sessao.execute(delete(Sessao).where(Sessao.usuario_id == usuario.id))
        return dados_usuario(usuario)


@rotas.put("/admin/cotas", dependencies=[Depends(administrador)])
def atualizar_cotas(payload: Limites):
    with fabrica_sessoes().begin() as sessao:
        global_ = sessao.scalar(select(LimiteGlobal).where(LimiteGlobal.id == 1).with_for_update())
        global_.limite_input, global_.limite_output = payload.limite_input, payload.limite_output
    return payload


@rotas.get("/admin/painel", dependencies=[Depends(administrador)])
def painel(dias: int = 30):
    if dias not in (7, 30, 90):
        raise HTTPException(422, "Selecione 7, 30 ou 90 dias.")
    with fabrica_sessoes()() as sessao:
        filtro = Chamada.criado_em >= agora() - timedelta(days=dias)
        soma = lambda coluna: func.coalesce(func.sum(coluna), 0)
        totais = sessao.execute(select(soma(Chamada.input), soma(Chamada.output), soma(Chamada.cache),
                                      func.count(), func.coalesce(func.avg(Chamada.duracao_ms), 0)).where(filtro)).one()
        dia = func.substr(cast(Chamada.criado_em, String), 1, 10)
        diario = sessao.execute(select(dia, soma(Chamada.input), soma(Chamada.output))
                               .where(filtro).group_by(dia).order_by(dia)).all()
        modelos = sessao.execute(select(Chamada.modelo, Chamada.etapa, soma(Chamada.input), soma(Chamada.output), func.count())
                                 .where(filtro).group_by(Chamada.modelo, Chamada.etapa)).all()
        recentes = sessao.execute(select(Chamada, Usuario.nome).join(Usuario, Usuario.id == Chamada.usuario_id)
                                  .where(filtro).order_by(Chamada.criado_em.desc()).limit(30)).all()
        global_ = sessao.get(LimiteGlobal, 1)
        return {"input": totais[0], "output": totais[1], "cache": totais[2],
                "chamadas": totais[3], "latencia_ms": round(float(totais[4])),
                "clientes_ativos": sessao.scalar(select(func.count()).select_from(Usuario).where(Usuario.ativo.is_(True), Usuario.perfil == "cliente")),
                "cotas": dados_consumo(sessao, "global", global_),
                "diario": [{"dia": linha[0], "input": linha[1], "output": linha[2]} for linha in diario],
                "modelos": [{"modelo": linha[0], "etapa": linha[1], "input": linha[2], "output": linha[3], "chamadas": linha[4]} for linha in modelos],
                "recentes": [{"id": chamada.id, "cliente": nome, "modelo": chamada.modelo, "etapa": chamada.etapa,
                              "input": chamada.input, "output": chamada.output, "status": chamada.status,
                              "trace_id": chamada.trace_id, "criado_em": chamada.criado_em} for chamada, nome in recentes]}