"""Layout base de todas as páginas protegidas (a "casca").

Monta: sidebar à esquerda + (topbar em cima da área de conteúdo). Você passa só o
miolo da página; a casca cuida do resto.

    def minha_pagina() -> rx.Component:
        return page_layout(
            rx.heading("Título"),
            rx.text("Conteúdo..."),
        )
"""

import reflex as rx

from components.sidebar import sidebar
from components.navbar import navbar
from state.auth_state import AuthState


def _spinner() -> rx.Component:
    """Tela de carregamento — fica no ar até sabermos se o usuário está logado."""
    return rx.center(
        rx.spinner(size="3"),
        width="100%",
        min_height="100vh",
    )


def _shell(*content: rx.Component) -> rx.Component:
    """A casca em si: sidebar + topbar + área de conteúdo."""
    return rx.hstack(
        sidebar(),
        rx.vstack(
            navbar(),
            rx.box(
                rx.vstack(
                    *content,
                    align="start",
                    spacing="6",
                    padding="40px 48px",
                    width="100%",
                ),
                flex="1",
                width="100%",
                background_color=rx.color("gray", 1),
                overflow_y="auto",
            ),
            spacing="0",
            flex="1",
            min_width="0",
            min_height="100vh",
            align="start",
        ),
        spacing="0",
        align="start",
        width="100%",
        min_height="100vh",
    )


def page_layout(*content: rx.Component) -> rx.Component:
    """Layout base das páginas protegidas, com guarda contra o "flash" de conteúdo.

    Só renderiza a casca quando a página JÁ hidratou (is_hydrated) E o usuário está
    logado. Enquanto isso, mostra o spinner. Assim, quem não está logado nunca chega a
    ver o conteúdo protegido — vê o spinner e é redirecionado pelo check_auth do on_load.
    """
    return rx.cond(
        rx.State.is_hydrated & AuthState.is_logged_in,
        _shell(*content),
        _spinner(),
    )
