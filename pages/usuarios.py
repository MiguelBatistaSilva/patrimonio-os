"""Tela de gestão de usuários — só admin (ver check_admin no app.py).

Lista os usuários e oferece: criar, editar (nome/papel), redefinir senha e ativar/desativar.
As senhas nunca aparecem (guardamos só o hash) — por isso "redefinir", nunca "ver".
"""

import reflex as rx

from components.layout import page_layout
from state.usuario_state import UsuarioState


def _campo_dlg(label: str, valor, on_change, **props) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.input(value=valor, on_change=on_change, width="100%", **props),
        spacing="1",
        align="start",
        width="100%",
    )


def _select_papel(valor, on_change) -> rx.Component:
    return rx.vstack(
        rx.text("Papel", size="2", weight="medium"),
        rx.select.root(
            rx.select.trigger(width="100%"),
            rx.select.content(
                rx.select.item("Operador", value="operador"),
                rx.select.item("Administrador", value="admin"),
                rx.select.item("Visualizador", value="visualizador"),
            ),
            value=valor,
            on_change=on_change,
        ),
        spacing="1",
        align="start",
        width="100%",
    )


def _erro_dialog() -> rx.Component:
    return rx.cond(
        UsuarioState.error_message != "",
        rx.text(UsuarioState.error_message, color=rx.color("red", 10), size="2"),
    )


def _dialog_criar() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(rx.icon("user-plus", size=16), "Novo usuário", size="3"),
        ),
        rx.dialog.content(
            rx.dialog.title("Novo usuário"),
            rx.dialog.description(
                "O usuário trocará esta senha no primeiro acesso.",
                size="2",
                color=rx.color("gray", 10),
            ),
            rx.vstack(
                _campo_dlg("Nome completo", UsuarioState.novo_nome, UsuarioState.set_novo_nome),
                _campo_dlg("CPF (login)", UsuarioState.novo_username, UsuarioState.set_novo_username),
                _campo_dlg(
                    "Senha inicial",
                    UsuarioState.nova_senha,
                    UsuarioState.set_nova_senha,
                    type="password",
                ),
                _select_papel(UsuarioState.novo_role, UsuarioState.set_novo_role),
                _erro_dialog(),
                rx.hstack(
                    rx.dialog.close(
                        rx.button("Cancelar", variant="soft", color_scheme="gray"),
                    ),
                    rx.button("Criar", on_click=UsuarioState.criar),
                    justify="end",
                    spacing="3",
                    width="100%",
                ),
                spacing="3",
                margin_top="12px",
            ),
            max_width="420px",
        ),
        open=UsuarioState.dialog_criar,
        on_open_change=UsuarioState.abrir_criar,
    )


def _dialog_editar() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Editar usuário"),
            rx.vstack(
                _campo_dlg("Nome completo", UsuarioState.edit_nome, UsuarioState.set_edit_nome),
                _select_papel(UsuarioState.edit_role, UsuarioState.set_edit_role),
                _erro_dialog(),
                rx.hstack(
                    rx.dialog.close(
                        rx.button("Cancelar", variant="soft", color_scheme="gray"),
                    ),
                    rx.button("Salvar", on_click=UsuarioState.salvar_edicao),
                    justify="end",
                    spacing="3",
                    width="100%",
                ),
                spacing="3",
                margin_top="12px",
            ),
            max_width="420px",
        ),
        open=UsuarioState.dialog_editar,
        on_open_change=UsuarioState.fechar_editar,
    )


def _dialog_reset() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Redefinir senha"),
            rx.dialog.description(
                rx.text("Nova senha para ", rx.text.strong(UsuarioState.reset_nome), "."),
                size="2",
                color=rx.color("gray", 10),
            ),
            rx.vstack(
                _campo_dlg(
                    "Nova senha",
                    UsuarioState.reset_senha,
                    UsuarioState.set_reset_senha,
                    type="password",
                ),
                _erro_dialog(),
                rx.hstack(
                    rx.dialog.close(
                        rx.button("Cancelar", variant="soft", color_scheme="gray"),
                    ),
                    rx.button("Redefinir", on_click=UsuarioState.redefinir),
                    justify="end",
                    spacing="3",
                    width="100%",
                ),
                spacing="3",
                margin_top="12px",
            ),
            max_width="420px",
        ),
        open=UsuarioState.dialog_reset,
        on_open_change=UsuarioState.fechar_reset,
    )


def _linha(u) -> rx.Component:
    return rx.table.row(
        rx.table.cell(u.nome),
        rx.table.cell(u.username),
        rx.table.cell(
            rx.badge(
                rx.match(
                    u.role,
                    ("admin", "Administrador"),
                    ("visualizador", "Visualizador"),
                    "Operador",
                ),
                color_scheme=rx.match(
                    u.role,
                    ("admin", "purple"),
                    ("visualizador", "blue"),
                    "gray",
                ),
            ),
        ),
        rx.table.cell(
            rx.cond(
                u.ativo,
                rx.badge("Ativo", color_scheme="green"),
                rx.badge("Inativo", color_scheme="gray"),
            ),
        ),
        rx.table.cell(
            rx.hstack(
                rx.button(
                    rx.icon("pencil", size=14),
                    on_click=UsuarioState.abrir_editar(u.id, u.nome, u.role),
                    size="1",
                    variant="soft",
                    color_scheme="gray",
                ),
                rx.button(
                    rx.icon("key-round", size=14),
                    on_click=UsuarioState.abrir_reset(u.id, u.nome),
                    size="1",
                    variant="soft",
                    color_scheme="gray",
                ),
                rx.cond(
                    u.ativo,
                    rx.button(
                        rx.icon("ban", size=14),
                        on_click=UsuarioState.alternar_ativo(u.id, u.ativo),
                        size="1",
                        variant="soft",
                        color_scheme="red",
                    ),
                    rx.button(
                        rx.icon("rotate-ccw", size=14),
                        on_click=UsuarioState.alternar_ativo(u.id, u.ativo),
                        size="1",
                        variant="soft",
                        color_scheme="green",
                    ),
                ),
                spacing="2",
            ),
        ),
    )


def usuarios_page() -> rx.Component:
    return page_layout(
        rx.hstack(
            rx.heading("Usuários", size="7"),
            rx.spacer(),
            _dialog_criar(),
            width="100%",
            align="center",
        ),
        rx.text(
            "Quem pode acessar o sistema. Só administradores gerenciam esta lista.",
            color=rx.color("gray", 10),
        ),
        rx.cond(
            UsuarioState.error_message != "",
            rx.text(UsuarioState.error_message, color=rx.color("red", 10), size="2"),
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Nome"),
                    rx.table.column_header_cell("CPF"),
                    rx.table.column_header_cell("Papel"),
                    rx.table.column_header_cell("Status"),
                    rx.table.column_header_cell("Ações"),
                ),
            ),
            rx.table.body(rx.foreach(UsuarioState.itens, _linha)),
            variant="surface",
            width="100%",
        ),
        # Diálogos de editar e redefinir (abertos via botões nas linhas).
        _dialog_editar(),
        _dialog_reset(),
    )
