"""Pipeline de Dados: chamados lidos do CATINET, onde o operador vê o que o scraper trouxe e APROVA ou DECLINA.

Aprovar cria a O.S. (com o que o chamado já informa); declinar descarta. Nada vira O.S.
sem um clique de uma pessoa.
"""

import reflex as rx

from components.layout import page_layout
from models.chamado import STATUS_APROVADO, STATUS_DECLINADO, STATUS_PENDENTE
from state.catinet_state import ChamadosState


def _acoes(c) -> rx.Component:
    return rx.cond(
        ChamadosState.filtro == STATUS_PENDENTE,
        rx.hstack(
            rx.button(
                rx.icon("check", size=14),
                "Aprovar",
                on_click=ChamadosState.aprovar(c.id),
                size="1",
                color_scheme="green",
            ),
            rx.button(
                rx.icon("x", size=14),
                "Declinar",
                on_click=ChamadosState.declinar(c.id),
                size="1",
                variant="soft",
                color_scheme="red",
            ),
            spacing="2",
        ),
        rx.cond(
            c.os_numero != "",
            rx.text("O.S. " + c.os_numero, size="2", weight="medium"),
            rx.text("—", color=rx.color("gray", 9)),
        ),
    )


def _linha(c) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(c.referencia, weight="bold", white_space="nowrap")),
        rx.table.cell(rx.text(c.data, size="2", white_space="nowrap")),
        rx.table.cell(
            rx.vstack(
                rx.text(c.solicitante, size="2"),
                rx.text(c.telefone, size="1", color=rx.color("gray", 10)),
                spacing="0",
                align="start",
            )
        ),
        rx.table.cell(rx.text(c.departamento, size="2")),
        rx.table.cell(
            rx.vstack(
                rx.text(c.item, size="2"),
                rx.text(c.categoria, size="1", color=rx.color("gray", 10)),
                spacing="0",
                align="start",
            )
        ),
        rx.table.cell(
            rx.text(
                c.descricao,
                size="2",
                white_space="pre-wrap",
                max_width="420px",
                style={
                    "display": "-webkit-box",
                    "-webkit-line-clamp": "4",
                    "-webkit-box-orient": "vertical",
                    "overflow": "hidden",
                },
                title=c.descricao,
            )
        ),
        rx.table.cell(_acoes(c)),
    )


def _tabela() -> rx.Component:
    return rx.cond(
        ChamadosState.chamados.length() > 0,
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Chamado"),
                    rx.table.column_header_cell("Registro"),
                    rx.table.column_header_cell("Solicitante"),
                    rx.table.column_header_cell("Departamento"),
                    rx.table.column_header_cell("Item / Categoria"),
                    rx.table.column_header_cell("Notas"),
                    rx.table.column_header_cell(
                        rx.cond(ChamadosState.filtro == STATUS_PENDENTE, "Decisão", "O.S.")
                    ),
                ),
            ),
            rx.table.body(rx.foreach(ChamadosState.chamados, _linha)),
            variant="surface",
            width="100%",
        ),
        rx.text("Nenhum chamado nesta lista.", size="2", color=rx.color("gray", 10)),
    )


def chamados_page() -> rx.Component:
    return page_layout(
        rx.hstack(
            rx.heading("Pipeline de Dados", size="7"),
            rx.spacer(),
            rx.button(
                rx.cond(
                    ChamadosState.buscando,
                    rx.spinner(size="2"),
                    rx.icon("refresh-cw", size=16),
                ),
                rx.cond(ChamadosState.buscando, "Buscando...", "Buscar chamados"),
                on_click=ChamadosState.buscar,
                disabled=ChamadosState.buscando,
                size="3",
            ),
            width="100%",
            align="center",
        ),
        rx.text(
            "Chamados lidos da fila do CATINET. Aprove para criar a O.S. ou declinar para descartar.",
            size="2",
            color=rx.color("gray", 10),
        ),
        rx.text(
            ChamadosState.ultima_busca,
            size="1",
            color=rx.cond(ChamadosState.ultima_busca_erro, rx.color("red", 10), rx.color("gray", 10)),
        ),
        rx.cond(
            ChamadosState.erro != "",
            rx.callout.root(
                rx.callout.icon(rx.icon("triangle-alert")),
                rx.callout.text(ChamadosState.erro),
                color_scheme="red",
                width="100%",
            ),
        ),
        rx.cond(
            ChamadosState.mensagem != "",
            rx.callout.root(
                rx.callout.icon(rx.icon("circle-check")),
                rx.callout.text(ChamadosState.mensagem),
                color_scheme="green",
                width="100%",
            ),
        ),
        rx.segmented_control.root(
            rx.segmented_control.item(
                "Pendentes (" + ChamadosState.n_pendentes.to_string() + ")",
                value=STATUS_PENDENTE,
            ),
            rx.segmented_control.item("Aprovados", value=STATUS_APROVADO),
            rx.segmented_control.item("Declinados", value=STATUS_DECLINADO),
            value=ChamadosState.filtro,
            on_change=ChamadosState.set_filtro,
        ),
        _tabela(),
    )
