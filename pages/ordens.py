"""Lista de Ordens de Serviço — a tela inicial do módulo de O.S.

Tabela simples (mais recentes primeiro) + botão para abrir o formulário de criação.
A coluna de ações (ver detalhe) entra na sub-etapa 3c.
"""

import reflex as rx

from components.layout import page_layout
from state.os_state import OsState


def _cor_status(status) -> str:
    # Verde = concluída, vermelho = cancelada, cinza = pendente.
    return rx.match(
        status,
        ("Concluída", "green"),
        ("Cancelada", "red"),
        "gray",
    )


def _linha(o) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(o.numero, weight="bold")),
        rx.table.cell(o.data_abertura),
        rx.table.cell(o.modalidade),
        rx.table.cell(rx.badge(o.status, color_scheme=_cor_status(o.status))),
        rx.table.cell(
            rx.link(
                rx.button("Abrir", size="1", variant="soft"),
                href="/ordens/" + o.id.to_string(),
            ),
        ),
    )


def _rotulo_campo(label: str, controle: rx.Component) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="1", color=rx.color("gray", 10)),
        controle,
        spacing="1",
        align="start",
    )


def _filtros() -> rx.Component:
    return rx.hstack(
        _rotulo_campo(
            "Status",
            rx.select.root(
                rx.select.trigger(width="160px"),
                rx.select.content(
                    rx.select.item("Todos", value="todos"),
                    rx.select.item("Pendente", value="Pendente"),
                    rx.select.item("Concluída", value="Concluída"),
                    rx.select.item("Cancelada", value="Cancelada"),
                ),
                value=OsState.filtro_status,
                on_change=OsState.set_filtro_status,
            ),
        ),
        _rotulo_campo(
            "Modalidade",
            rx.select.root(
                rx.select.trigger(width="200px"),
                rx.select.content(
                    rx.select.item("Todas", value="todas"),
                    rx.foreach(
                        OsState.opts_modalidade,
                        lambda o: rx.select.item(o.nome, value=o.valor),
                    ),
                ),
                value=OsState.filtro_modalidade,
                on_change=OsState.set_filtro_modalidade,
            ),
        ),
        _rotulo_campo(
            "De",
            rx.input(
                type="date",
                value=OsState.filtro_data_de,
                on_change=OsState.set_filtro_data_de,
            ),
        ),
        _rotulo_campo(
            "Até",
            rx.input(
                type="date",
                value=OsState.filtro_data_ate,
                on_change=OsState.set_filtro_data_ate,
            ),
        ),
        rx.button(
            "Limpar",
            on_click=OsState.limpar_filtros,
            variant="soft",
            color_scheme="gray",
        ),
        spacing="3",
        align="end",
        wrap="wrap",
        width="100%",
    )


def ordens_page() -> rx.Component:
    return page_layout(
        rx.hstack(
            rx.heading("Ordens de Serviço", size="7"),
            rx.spacer(),
            rx.link(
                rx.button(rx.icon("plus", size=16), "Nova O.S.", size="3"),
                href="/ordens/nova",
            ),
            width="100%",
            align="center",
        ),
        _filtros(),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Número"),
                    rx.table.column_header_cell("Abertura"),
                    rx.table.column_header_cell("Modalidade"),
                    rx.table.column_header_cell("Status"),
                    rx.table.column_header_cell(""),
                ),
            ),
            rx.table.body(
                rx.foreach(OsState.ordens, _linha),
            ),
            variant="surface",
            width="100%",
        ),
    )
