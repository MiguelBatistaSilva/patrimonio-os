"""Funções de segurança — guardar e conferir senhas com bcrypt.

NUNCA guardamos a senha em texto puro no banco. Guardamos um "hash": um embaralhamento
de mão única. Dá pra verificar se uma senha bate com o hash, mas é inviável voltar do
hash para a senha original. Se o banco vazar, as senhas continuam protegidas.
"""

import bcrypt


def hash_password(senha: str) -> str:
    """Recebe a senha em texto puro e devolve o hash (que vai para o banco).

    gensalt() gera um "sal" aleatório embutido no próprio hash — por isso dois usuários
    com a mesma senha geram hashes diferentes.
    """
    hash_bytes = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())
    return hash_bytes.decode("utf-8")


def verify_password(senha: str, hash_armazenado: str) -> bool:
    """Confere se a senha digitada bate com o hash guardado. Usada no login."""
    return bcrypt.checkpw(senha.encode("utf-8"), hash_armazenado.encode("utf-8"))
