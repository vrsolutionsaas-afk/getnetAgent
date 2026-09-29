from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import obter_config


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "portal_usuarios"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    senha_hash: Mapped[str] = mapped_column(Text)
    perfil: Mapped[str] = mapped_column(String(10), default="cliente")
    cliente_id: Mapped[str] = mapped_column(String(64))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    limite_input: Mapped[int] = mapped_column(Integer, default=200000)
    limite_output: Mapped[int] = mapped_column(Integer, default=50000)


class Sessao(Base):
    __tablename__ = "portal_sessoes"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("portal_usuarios.id"))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TentativaLogin(Base):
    __tablename__ = "portal_tentativas_login"
    chave: Mapped[str] = mapped_column(String(64), primary_key=True)
    quantidade: Mapped[int] = mapped_column(Integer, default=0)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class LimiteGlobal(Base):
    __tablename__ = "portal_limite_global"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    limite_input: Mapped[int] = mapped_column(Integer, default=2000000)
    limite_output: Mapped[int] = mapped_column(Integer, default=500000)


class Consumo(Base):
    __tablename__ = "portal_consumo_mensal"
    escopo: Mapped[str] = mapped_column(String(64), primary_key=True)
    mes: Mapped[str] = mapped_column(String(7), primary_key=True)
    input: Mapped[int] = mapped_column(Integer, default=0)
    output: Mapped[int] = mapped_column(Integer, default=0)
    reservado_input: Mapped[int] = mapped_column(Integer, default=0)
    reservado_output: Mapped[int] = mapped_column(Integer, default=0)


class Chamada(Base):
    __tablename__ = "portal_chamadas"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("portal_usuarios.id"), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    mes: Mapped[str] = mapped_column(String(7))
    modelo: Mapped[str] = mapped_column(String(100))
    etapa: Mapped[str] = mapped_column(String(40))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    input: Mapped[int] = mapped_column(Integer, default=0)
    output: Mapped[int] = mapped_column(Integer, default=0)
    cache: Mapped[int] = mapped_column(Integer, default=0)
    reservado_input: Mapped[int] = mapped_column(Integer)
    reservado_output: Mapped[int] = mapped_column(Integer)
    duracao_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="reservado")


class Conversa(Base):
    __tablename__ = "portal_conversas"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("portal_usuarios.id"), index=True)
    titulo: Mapped[str] = mapped_column(String(100))
    processando_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class Mensagem(Base):
    __tablename__ = "portal_mensagens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversa_id: Mapped[str] = mapped_column(ForeignKey("portal_conversas.id"), index=True)
    papel: Mapped[str] = mapped_column(String(16))
    texto: Mapped[str] = mapped_column(Text)
    fontes: Mapped[list] = mapped_column(JSON, default=list)
    agente: Mapped[str] = mapped_column(String(40), default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


@lru_cache
def fabrica_sessoes():
    config = obter_config()
    url = config.portal_database_url or config.url_postgres
    engine = create_engine(url, pool_pre_ping=True)
    return sessionmaker(engine, expire_on_commit=False)


def inicializar() -> None:
    fabrica = fabrica_sessoes()
    Base.metadata.create_all(fabrica.kw["bind"])
    with fabrica.begin() as sessao:
        if sessao.get(LimiteGlobal, 1) is None:
            sessao.add(LimiteGlobal(id=1))