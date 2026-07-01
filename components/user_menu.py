"""Menu do usuário logado — fica no rodapé da sidebar.

Mostra o nome, abre um dropdown com Configurações, alternar tema claro/escuro e Sair.
Adapta-se ao estado colapsado/expandido da sidebar.

(Era uma classe só de @staticmethod no projeto antigo; aqui virou funções soltas — o
estilo idiomático que combinamos. As funções com "_" na frente são auxiliares internas.)
"""

import reflex as rx

from state.auth_state import AuthState
from state.sidebar_state import SidebarState


def _trigger() -> rx.Component:
    """O botão que abre o menu. Expandido mostra o nome; contraído, só o ícone."""
    return rx.button(
        rx.icon("user-circle", size=15, flex_shrink="0"),
        rx.cond(
            ~SidebarState.collapsed,
            rx.fragment(
                rx.text(
                    AuthState.nome,
                    size="2",
                    white_space="nowrap",
                    overflow="hidden",
                    flex="1",
                    text_align="left",
                ),
                rx.icon("chevrons-up-down", size=13, color=rx.color("gray", 10)),
            ),
            rx.fragment(),
        ),
        variant="soft",
        color_scheme="gray",
        width="95%",
        height="40px",
        justify="start",
        cursor="pointer",
    )


def _menu() -> rx.Component:
    return rx.dropdown_menu.content(
        rx.dropdown_menu.item(
            rx.hstack(
                rx.icon("settings", size=14),
                rx.text("Configurações", size="2"),
                spacing="2",
                align="center",
            ),
        ),
        rx.dropdown_menu.item(
            rx.hstack(
                rx.color_mode_cond(
                    rx.icon("moon", size=14),
                    rx.icon("sun", size=14),
                ),
                rx.color_mode_cond(
                    rx.text("Modo Escuro", size="2"),
                    rx.text("Modo Claro", size="2"),
                ),
                spacing="2",
                align="center",
            ),
            on_click=rx.toggle_color_mode,
        ),
        rx.dropdown_menu.separator(),
        rx.dropdown_menu.item(
            rx.hstack(
                rx.icon("log-out", size=14),
                rx.text("Sair", size="2"),
                spacing="2",
                align="center",
            ),
            on_click=AuthState.logout,
            color="red",
        ),
        side="top",
        align="start",
    )


def user_menu() -> rx.Component:
    return rx.box(
        rx.center(
            rx.dropdown_menu.root(
                rx.dropdown_menu.trigger(_trigger(), as_child=True),
                _menu(),
                width="90%",
            ),
            width="100%",
        ),
        width="100%",
        padding_top="4px",
        padding_bottom="8px",
        padding_x="8px",
    )
