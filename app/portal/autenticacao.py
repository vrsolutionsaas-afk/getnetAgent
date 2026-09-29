import hashlib
import secrets
from datetime import timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.portal.banco import Sessao, Usuario, agora, fabrica_sessoes

bearer = HTTPBearer(auto_error=False)


def hash_senha(senha: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    derivada = hashlib.scrypt(senha.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f"scrypt${salt}${derivada}"


def verificar_senha(senha: str, armazenada: str) -> bool:
    try:
        _, salt, _ = armazenada.split("$")
        return secrets.compare_digest(hash_senha(senha, salt), armazenada)
    except (ValueError, TypeError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def nova_sessao(usuario_id: str) -> str:
    token = secrets.token_urlsafe(48)
    with fabrica_sessoes().begin() as sessao:
        sessao.add(Sessao(token_hash=hash_token(token), usuario_id=usuario_id,
                          expira_em=agora() + timedelta(hours=12)))
    return token


def usuario_atual(credencial: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Usuario:
    if credencial is None:
        raise HTTPException(401, "Entre na sua conta para continuar.")
    with fabrica_sessoes()() as sessao:
        acesso = sessao.get(Sessao, hash_token(credencial.credentials))
        if not acesso or acesso.expira_em.replace(tzinfo=timezone.utc) <= agora():
            raise HTTPException(401, "Sessao expirada. Entre novamente.")
        usuario = sessao.get(Usuario, acesso.usuario_id)
        if not usuario or not usuario.ativo:
            raise HTTPException(401, "Acesso indisponivel.")
        return usuario


def administrador(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    if usuario.perfil != "admin":
        raise HTTPException(403, "Acesso restrito a administradores.")
    return usuario