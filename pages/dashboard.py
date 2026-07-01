"""Dashboard — visão geral das Ordens de Serviço.

Cartões com a contagem por status + um gráfico de barras simples por modalidade.
Tudo é só leitura, carregado no on_load (ver app.py).
"""

import reflex as rx

from components.layout import page_layout
from state.auth_state import AuthState
from state.dashboard_state import DashboardState


def _card(label: str, valor, cor: str) -> rx.Component:
    """Cartão de contador: rótulo pequeno + número grande colorido."""
    return rx.card(
        rx.vstack(
            rx.text(label, size="2", color=rx.color("gray", 10)),
            rx.heading(valor, size="8", color=rx.color(cor, 11)),
            spacing="1",
            align="start",
        ),
        width="100%",
    )


def _barra(b) -> rx.Component:
    """Uma linha do gráfico: nome + quantidade em cima, barra proporcional embaixo."""
    return rx.vstack(
        rx.hstack(
            rx.text(b.nome, size="2"),
            rx.spacer(),
            rx.text(b.qtd, size="2", weight="bold"),
            width="100%",
        ),
        rx.box(
            rx.box(
                width=b.pct.to_string() + "%",
                height="8px",
                background_color=rx.color("accent", 9),
                border_radius="4px",
            ),
            width="100%",
            height="8px",
            background_color=rx.color("gray", 4),
            border_radius="4px",
        ),
        spacing="1",
        width="100%",
    )


def dashboard_page() -> rx.Component:
    return page_layout(
        rx.heading("Dashboard", size="7"),
        rx.text("Bem-vindo, ", rx.text.strong(AuthState.nome), "!"),
        rx.grid(
            _card("Total", DashboardState.total, "gray"),
            _card("Pendentes", DashboardState.pendentes, "amber"),
            _card("Concluídas", DashboardState.concluidas, "green"),
            _card("Canceladas", DashboardState.canceladas, "red"),
            columns="4",
            spacing="4",
            width="100%",
        ),
        rx.heading("Por modalidade", size="4", margin_top="8px"),
        rx.cond(
            DashboardState.por_modalidade.length() > 0,
            rx.vstack(
                rx.foreach(DashboardState.por_modalidade, _barra),
                spacing="3",
                width="100%",
            ),
            rx.text("Nenhuma O.S. cadastrada ainda.", size="2", color=rx.color("gray", 10)),
        ),
    )
