"""Acesso a dados da tabela `user` (CRUD = Create, Read, Update, Delete).

Por que uma camada separada? Para o State (cérebro da tela) NUNCA precisar saber SQL.
Ele só chama authenticate_user(...) e recebe um User ou None. Toda conversa com o
banco sobre usuários mora aqui — fica fácil achar, testar e reaproveitar.
"""

from sqlalchemy.orm import Session

from models.user import User
from services.security import verify_password, hash_password


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Confere login + senha. Devolve o User se baterem; senão, None.

    Três condições para entrar:
    1. o usuário precisa existir,
    2. precisa estar ativo (ativo=True),
    3. a senha digitada precisa bater com o hash guardado (via bcrypt).
    """
    user = db.query(User).filter_by(username=username).first()
    if user is None or not user.ativo:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# ── CRUD de usuários (gestão feita pelo admin) ──

def listar(db: Session) -> list[User]:
    """READ — todos os usuários, em ordem alfabética de nome."""
    return db.query(User).order_by(User.nome).all()


def _obter(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("Usuário não encontrado.")
    return user


def criar(db: Session, nome: str, username: str, password: str, role: str) -> User:
    """CREATE — cria o usuário com a senha já 'hasheada' e marcada como provisória.

    senha_provisoria nasce True (default do model): o usuário troca no 1º acesso.
    """
    nome = nome.strip()
    username = username.strip()
    if not nome or not username:
        raise ValueError("Nome e CPF são obrigatórios.")
    if not password:
        raise ValueError("Defina uma senha inicial.")
    if db.query(User).filter_by(username=username).first():
        raise ValueError(f"Já existe um usuário com o CPF {username}.")

    user = User(
        nome=nome,
        username=username,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    return user


def editar(db: Session, user_id: int, nome: str, role: str) -> User:
    """UPDATE — altera nome e papel (não mexe na senha)."""
    nome = nome.strip()
    if not nome:
        raise ValueError("O nome é obrigatório.")
    user = _obter(db, user_id)
    user.nome = nome
    user.role = role
    db.commit()
    return user


def definir_ativo(db: Session, user_id: int, ativo: bool) -> User:
    """Ativa/desativa o acesso do usuário (soft delete — preserva o histórico)."""
    user = _obter(db, user_id)
    user.ativo = ativo
    db.commit()
    return user


def redefinir_senha(db: Session, user_id: int, nova_senha: str) -> User:
    """Admin redefine a senha de alguém. Volta a ser provisória (troca no próximo acesso)."""
    if not nova_senha:
        raise ValueError("Defina a nova senha.")
    user = _obter(db, user_id)
    user.password_hash = hash_password(nova_senha)
    user.senha_provisoria = True
    db.commit()
    return user


def trocar_senha(db: Session, user_id: int, nova_senha: str) -> User:
    """Usuário troca a PRÓPRIA senha — deixa de ser provisória."""
    if not nova_senha:
        raise ValueError("Defina a nova senha.")
    user = _obter(db, user_id)
    user.password_hash = hash_password(nova_senha)
    user.senha_provisoria = False
    db.commit()
    return user
