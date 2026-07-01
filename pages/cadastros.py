"""Tela de Cadastros — CRUD dos 6 domínios em uma página só, com abas.

Só admin acessa (ver o on_load=check_admin no app.py). A tela conversa apenas com o
DominioState; quem fala com o banco é o crud, lá atrás.
"""

import reflex as rx

from components.layout import page_layout
from state.dominio_state import DominioState
from crud.dominio import DOMINIOS


def _linha(item) -> rx.Component:
    """Uma linha da tabela. Em modo edição, o nome vira um input; senão, é só texto."""
    em_edicao = DominioState.editando_id == item.id

    return rx.table.row(
        rx.table.cell(
            rx.cond(
                em_edicao,
                rx.input(
                    value=DominioState.edit_nome,
                    on_change=DominioState.set_edit_nome,
                    size="2",
                ),
                rx.text(item.nome),
            ),
        ),
        rx.table.cell(
            rx.cond(
                item.ativo,
                rx.badge("Ativo", color_scheme="green"),
                rx.badge("Inativo", color_scheme="gray"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                em_edicao,
                rx.hstack(
                    rx.button("Salvar", on_click=DominioState.salvar_edicao, size="1"),
                    rx.button(
                        "Cancelar",
                        on_click=DominioState.cancelar_edicao,
                        size="1",
                        variant="soft",
                        color_scheme="gray",
                    ),
                    spacing="2",
                ),
                rx.hstack(
                    rx.button(
                        rx.icon("pencil", size=14),
                        on_click=DominioState.iniciar_edicao(item.id, item.nome),
                        size="1",
                        variant="soft",
                        color_scheme="gray",
                    ),
                    rx.cond(
                        item.ativo,
                        rx.button(
                            rx.icon("ban", size=14),
                            on_click=DominioState.desativar(item.id),
                            size="1",
                            variant="soft",
                            color_scheme="red",
                        ),
                        rx.button(
                            rx.icon("rotate-ccw", size=14),
                            on_click=DominioState.reativar(item.id),
                            size="1",
                            variant="soft",
                            color_scheme="green",
                        ),
                    ),
                    spacing="2",
                ),
            ),
        ),
    )


def cadastros_page() -> rx.Component:
    return page_layout(
        rx.heading("Cadastros", size="7"),
        rx.text(
            "Gerencie as listas usadas nos formulários de Ordem de Serviço.",
            color=rx.color("gray", 10),
        ),
        # Abas: uma por domínio, geradas a partir do registro DOMINIOS.
        rx.tabs.root(
            rx.tabs.list(
                *[
                    rx.tabs.trigger(rotulo, value=chave)
                    for chave, (rotulo, _model) in DOMINIOS.items()
                ],
            ),
            value=DominioState.tabela_atual,
            on_change=DominioState.selecionar_tabela,
            width="100%",
        ),
        # Adicionar
        rx.hstack(
            rx.input(
                placeholder="Novo registro...",
                value=DominioState.novo_nome,
                on_change=DominioState.set_novo_nome,
                width="320px",
                size="3",
            ),
            rx.button(
                rx.icon("plus", size=16),
                "Adicionar",
                on_click=DominioState.adicionar,
                size="3",
            ),
            spacing="3",
            align="center",
        ),
        rx.cond(
            DominioState.error_message != "",
            rx.text(DominioState.error_message, color=rx.color("red", 10), size="2"),
        ),
        # Tabela
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Nome"),
                    rx.table.column_header_cell("Situação"),
                    rx.table.column_header_cell("Ações"),
                ),
            ),
            rx.table.body(
                rx.foreach(DominioState.itens, _linha),
            ),
            variant="surface",
            width="100%",
        ),
    )
