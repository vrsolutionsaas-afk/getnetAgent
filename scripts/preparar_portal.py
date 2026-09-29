from uuid import uuid4

from sqlalchemy import select

from app.config import obter_config
from app.portal.autenticacao import hash_senha
from app.portal.banco import Usuario, fabrica_sessoes, inicializar


def main() -> None:
    inicializar()
    config = obter_config()
    email = config.portal_admin_email.strip().lower()
    senha = config.portal_admin_senha
    with fabrica_sessoes().begin() as sessao:
        if not email or not senha:
            if sessao.scalar(select(Usuario).where(Usuario.perfil == "admin", Usuario.ativo.is_(True))) is not None:
                print("Portal inicializado. Administrador existente preservado.")
                return
            raise SystemExit("Defina PORTAL_ADMIN_EMAIL e PORTAL_ADMIN_SENHA (minimo 12 caracteres).")
        if "@" not in email or len(senha) < 12 or len(senha) > 128:
            raise SystemExit("Email ou senha inicial invalidos. Use senha de 12 a 128 caracteres.")
        existente = sessao.scalar(select(Usuario).where(Usuario.email == email))
        if existente:
            if existente.perfil != "admin":
                raise SystemExit("O email informado pertence a um cliente. Use outro email para o administrador.")
            print("Usuario ja existe. Nenhuma senha ou permissao foi alterada.")
            return
        sessao.add(Usuario(id=uuid4().hex, nome="Administrador Getnet", email=email,
                          senha_hash=hash_senha(senha), perfil="admin", cliente_id="cliente1988"))
    print("Portal inicializado e administrador criado.")


if __name__ == "__main__":
    main()