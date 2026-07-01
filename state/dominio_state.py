"""Cérebro da tela de Cadastros (CRUD dos 6 domínios).

UM state serve para os seis porque as tabelas têm a mesma forma: guardamos só a CHAVE
da tabela atual (ex.: "modalidade") e, dentro de cada handler, resolvemos a classe do
model pelo registro DOMINIOS. O state nunca guarda a classe do model em si (ela não é
"serializável" para o navegador) — guarda dados simples: textos, números e a lista
de itens já convertida para uma forma leve (ItemDominio).
"""

from dataclasses import dataclass

import reflex as rx

from services.database import SessionLocal
from crud import dominio as crud_dominio
from crud.dominio import DOMINIOS


@dataclass
class ItemDominio:
    """Versão "leve" de uma linha, só com o que a tela precisa mostrar.

    Não mandamos o objeto do SQLAlchemy direto para a tela: convertemos para este
    formato simples. Assim a tela não fica acoplada ao banco.
    """

    id: int
    nome: str
    ativo: bool


class DominioState(rx.State):
    tabela_atual: str = "modalidade"   # qual aba está selecionada
    itens: list[ItemDominio] = []      # linhas da tabela atual

    # Formulário de adicionar
    novo_nome: str = ""
    error_message: str = ""

    # Edição inline de uma linha (0 = ninguém em edição, pois os ids começam em 1)
    editando_id: int = 0
    edit_nome: str = ""

    # ── Setters (escritos à mão; ver gotcha do projeto) ──
    def set_novo_nome(self, value: str):
        self.novo_nome = value

    def set_edit_nome(self, value: str):
        self.edit_nome = value

    @rx.var
    def titulo_atual(self) -> str:
        return DOMINIOS[self.tabela_atual][0]

    # ── Helper interno: recarrega self.itens usando uma sessão já aberta ──
    def _recarregar(self, db):
        Model = DOMINIOS[self.tabela_atual][1]
        registros = crud_dominio.listar(db, Model, incluir_inativos=True)
        self.itens = [
            ItemDominio(id=r.id, nome=r.nome, ativo=r.ativo) for r in registros
        ]

    # ── READ ──
    def carregar(self):
        """Chamado no on_load da página e ao trocar de aba."""
        db = SessionLocal()
        try:
            self._recarregar(db)
        finally:
            db.close()

    def selecionar_tabela(self, chave: str):
        self.tabela_atual = chave
        self.error_message = ""
        self.novo_nome = ""
        self.editando_id = 0
        self.carregar()

    # ── CREATE ──
    def adicionar(self):
        self.error_message = ""
        db = SessionLocal()
        try:
            Model = DOMINIOS[self.tabela_atual][1]
            crud_dominio.criar(db, Model, self.novo_nome)
            self.novo_nome = ""
            self._recarregar(db)
        except ValueError as erro:
            self.error_message = str(erro)  # mensagem amigável vinda do crud
        finally:
            db.close()

    # ── UPDATE ──
    def iniciar_edicao(self, item_id: int, nome: str):
        self.editando_id = item_id
        self.edit_nome = nome
        self.error_message = ""

    def cancelar_edicao(self):
        self.editando_id = 0
        self.edit_nome = ""

    def salvar_edicao(self):
        self.error_message = ""
        db = SessionLocal()
        try:
            Model = DOMINIOS[self.tabela_atual][1]
            crud_dominio.editar(db, Model, self.editando_id, self.edit_nome)
            self.editando_id = 0
            self.edit_nome = ""
            self._recarregar(db)
        except ValueError as erro:
            self.error_message = str(erro)
        finally:
            db.close()

    # ── DELETE (soft) e seu par reativar ──
    def desativar(self, item_id: int):
        db = SessionLocal()
        try:
            Model = DOMINIOS[self.tabela_atual][1]
            crud_dominio.desativar(db, Model, item_id)
            self._recarregar(db)
        finally:
            db.close()

    def reativar(self, item_id: int):
        db = SessionLocal()
        try:
            Model = DOMINIOS[self.tabela_atual][1]
            crud_dominio.reativar(db, Model, item_id)
            self._recarregar(db)
        finally:
            db.close()
