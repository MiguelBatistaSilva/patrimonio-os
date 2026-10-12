"""Topbar — a barra fina no topo da área de conteúdo.

Tem o sino de notificações: mostra quantos chamados do CATINET esperam decisão no
Pipeline de Dados. A contagem é relida ao montar a topbar (a cada página que se abre) e
a cada minuto, por um relógio escondido — sem isso o número só mudaria ao trocar de página.
"""

import reflex as rx

from state.auth_state import AuthState
from state.catinet_state import AlertasState


def _selo() -> rx.Component:
    """A bolinha vermelha com o número, no canto do sino. Some quando não há pendentes."""
    return rx.cond(
        AlertasState.n_pendentes > 0,
        rx.box(
            rx.text(
                rx.cond(AlertasState.n_pendentes > 99, "99+", AlertasState.n_pendentes),
                size="1",
                weight="bold",
                color="white",
                line_height="1",
            ),
            position="absolute",
            top="-6px",
            right="-8px",
            min_width="16px",
            height="16px",
            padding="0 4px",
            border_radius="8px",
            background_color=rx.color("red", 9),
            display="flex",
            align_items="center",
            justify_content="center",
        ),
    )


def _painel() -> rx.Component:
    return rx.popover.content(
        rx.vstack(
            rx.text("Pipeline de Dados", size="2", weight="bold"),
            rx.cond(
                AlertasState.n_pendentes > 0,
                rx.text(
                    AlertasState.n_pendentes.to_string()
                    + " chamado(s) do CATINET aguardando sua decisão.",
                    size="2",
                ),
                rx.text("Nenhum chamado aguardando decisão.", size="2"),
            ),
            rx.cond(
                AlertasState.ultima_busca != "",
                rx.text(
                    AlertasState.ultima_busca,
                    size="1",
                    color=rx.cond(
                        AlertasState.ultima_busca_erro, rx.color("red", 10), rx.color("gray", 10)
                    ),
                ),
            ),
            rx.link(
                rx.button("Abrir Pipeline de Dados", size="2", width="100%"),
                href="/pipeline",
                width="100%",
            ),
            spacing="2",
            align="start",
        ),
        width="300px",
    )


def _sino() -> rx.Component:
    return rx.popover.root(
        rx.popover.trigger(
            rx.box(
                rx.icon("bell", size=18, color=rx.color("gray", 10)),
                _selo(),
                position="relative",
                cursor="pointer",
            ),
        ),
        _painel(),
    )


def navbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.spacer(),
            # Operacional apenas: o visualizador não usa o pipeline.
            rx.cond(~AuthState.is_visualizador, _sino()),
            # Relógio escondido: a cada 60 s dispara o on_change e relê a contagem.
            rx.moment(
                interval=60000,
                on_change=AlertasState.atualizar_periodico,
                display="none",
            ),
            padding="0 24px",
            align="center",
            width="100%",
            height="100%",
        ),
        background_color=rx.color("gray", 1),
        border_bottom=f"1px solid {rx.color('gray', 6)}",
        width="100%",
        height="44px",
        flex_shrink="0",
        on_mount=AlertasState.carregar,
    )
