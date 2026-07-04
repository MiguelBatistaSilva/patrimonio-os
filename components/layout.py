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
    """Tela de carregamento de página INTEIRA — enquanto não sabemos se há login."""
    return rx.center(
        rx.spinner(size="3"),
        width="100%",
        min_height="100vh",
    )


def _conteudo_carregando() -> rx.Component:
    """Spinner só da ÁREA DE CONTEÚDO (a sidebar/topbar continuam no ar).

    Aparece por um instante a cada navegação, enquanto o on_load da nova página roda
    (nesse intervalo o Reflex deixa is_hydrated=False). É o que troca — não a casca."""
    return rx.center(
        rx.spinner(size="3"),
        width="100%",
        min_height="60vh",
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
    """Layout base das páginas protegidas.

    Dois portões, de propósito separados, para a sidebar NÃO piscar ao navegar:

    - Topo (`is_logged_in`): decide se mostra a CASCA ou o spinner de página inteira.
      Vem do LocalStorage e NÃO oscila durante a navegação — então, uma vez logado, a
      casca (sidebar + topbar) fica montada e estável entre as páginas.
    - Interno (`is_hydrated`): só a ÁREA DE CONTEÚDO. A cada navegação o Reflex zera o
      is_hydrated enquanto o on_load roda; aqui isso troca apenas o miolo por um spinner
      rápido, sem mexer na casca. Assim, quem não está logado nunca vê conteúdo protegido
      (o check_auth do on_load redireciona), e quem está logado só vê o conteúdo trocar.
    """
    return rx.cond(
        AuthState.is_logged_in,
        _shell(
            rx.cond(
                rx.State.is_hydrated,
                rx.fragment(*content),
                _conteudo_carregando(),
            ),
        ),
        _spinner(),
    )
