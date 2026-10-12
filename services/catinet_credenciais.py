"""Onde ficam as credenciais do CATINET.

- SENHA: no cofre do Windows (Gerenciador de Credenciais), via `keyring`. Nunca no banco,
  nunca em arquivo, nunca no código (o repositório é público). O cofre é por usuário do
  Windows: só quem roda o sistema nessa conta enxerga.
- USUÁRIO e LINK DA FILA: na tabela config_sistema (não são segredo).

Este módulo só cuida da SENHA; usuário e link são lidos/gravados por crud/chamado.py.
"""

import keyring
from keyring.errors import KeyringError

_SERVICO = "PatrimonioTJCE-CATINET"


def guardar_senha(usuario: str, senha: str) -> None:
    keyring.set_password(_SERVICO, usuario, senha)


def obter_senha(usuario: str) -> str | None:
    """A senha guardada para o usuário, ou None (sem cofre disponível também dá None)."""
    if not usuario:
        return None
    try:
        return keyring.get_password(_SERVICO, usuario)
    except KeyringError:
        return None


def apagar_senha(usuario: str) -> None:
    try:
        keyring.delete_password(_SERVICO, usuario)
    except KeyringError:
        pass  # já não existia
