"""Cérebro da tela de gestão de usuários (só admin).

Três diálogos: criar, editar (nome/papel) e redefinir senha. Cada um controlado por
um booleano de "aberto/fechado" no state, igual ao diálogo de concluir O.S.
"""

from dataclasses import dataclass

import reflex as rx

from services.database import SessionLocal
from crud import user as crud_user
from state.auth_state import AuthState


@dataclass
class ItemUsuario:
    id: int
    nome: str
    username: str
    role: str
    ativo: bool


class UsuarioState(rx.State):
    itens: list[ItemUsuario] = []
    error_message: str = ""

    # ── Criar ──
    dialog_criar: bool = False
    novo_nome: str = ""
    novo_username: str = ""
    nova_senha: str = ""
    novo_role: str = "operador"

    # ── Editar (nome + papel) ──
    dialog_editar: bool = False
    edit_id: int = 0
    edit_nome: str = ""
    edit_role: str = "operador"

    # ── Redefinir senha ──
    dialog_reset: bool = False
    reset_id: int = 0
    reset_nome: str = ""  # só para exibir de quem é
    reset_senha: str = ""

    # ── Setters (escritos à mão) ──
    def set_novo_nome(self, v: str):
        self.novo_nome = v

    def set_novo_username(self, v: str):
        self.novo_username = v

    def set_nova_senha(self, v: str):
        self.nova_senha = v

    def set_novo_role(self, v: str):
        self.novo_role = v

    def set_edit_nome(self, v: str):
        self.edit_nome = v

    def set_edit_role(self, v: str):
        self.edit_role = v

    def set_reset_senha(self, v: str):
        self.reset_senha = v

    # ── READ ──
    def carregar(self):
        db = SessionLocal()
        try:
            self.itens = [
                ItemUsuario(u.id, u.nome, u.username, u.role, u.ativo)
                for u in crud_user.listar(db)
            ]
        finally:
            db.close()

    # ── Criar ──
    def abrir_criar(self, aberto: bool):
        self.dialog_criar = aberto
        self.error_message = ""
        if aberto:
            self.novo_nome = ""
            self.novo_username = ""
            self.nova_senha = ""
            self.novo_role = "operador"

    def criar(self):
        self.error_message = ""
        db = SessionLocal()
        try:
            crud_user.criar(db, self.novo_nome, self.novo_username, self.nova_senha, self.novo_role)
        except ValueError as erro:
            self.error_message = str(erro)
            return
        finally:
            db.close()
        self.dialog_criar = False
        self.carregar()

    # ── Editar ──
    def abrir_editar(self, user_id: int, nome: str, role: str):
        self.dialog_editar = True
        self.error_message = ""
        self.edit_id = user_id
        self.edit_nome = nome
        self.edit_role = role

    def fechar_editar(self, aberto: bool):
        self.dialog_editar = aberto

    def salvar_edicao(self):
        self.error_message = ""
        db = SessionLocal()
        try:
            crud_user.editar(db, self.edit_id, self.edit_nome, self.edit_role)
        except ValueError as erro:
            self.error_message = str(erro)
            return
        finally:
            db.close()
        self.dialog_editar = False
        self.carregar()

    # ── Redefinir senha ──
    def abrir_reset(self, user_id: int, nome: str):
        self.dialog_reset = True
        self.error_message = ""
        self.reset_id = user_id
        self.reset_nome = nome
        self.reset_senha = ""

    def fechar_reset(self, aberto: bool):
        self.dialog_reset = aberto

    def redefinir(self):
        self.error_message = ""
        db = SessionLocal()
        try:
            crud_user.redefinir_senha(db, self.reset_id, self.reset_senha)
        except ValueError as erro:
            self.error_message = str(erro)
            return
        finally:
            db.close()
        self.dialog_reset = False
        self.carregar()

    # ── Ativar/desativar (com trava contra desativar a si mesmo) ──
    async def alternar_ativo(self, user_id: int, ativo_atual: bool):
        self.error_message = ""
        auth = await self.get_state(AuthState)
        if str(user_id) == auth.user_id and ativo_atual:
            self.error_message = "Você não pode desativar a si mesmo."
            return
        db = SessionLocal()
        try:
            crud_user.definir_ativo(db, user_id, not ativo_atual)
        finally:
            db.close()
        self.carregar()
