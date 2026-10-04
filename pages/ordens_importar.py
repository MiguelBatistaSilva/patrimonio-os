"""Importação em lote: cola uma lista de O.S. (ex.: do WhatsApp) e cria todas de uma vez.

Duas etapas, de propósito: "Analisar" só MOSTRA o que seria gravado (com os erros por
linha); só o botão "Gravar" escreve no banco.
"""

import reflex as rx

from components.layout import page_layout
from state.importacao_state import MODELO, ImportacaoState


def _ajuda() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("Modelo", size="2", weight="medium"),
            # Caixa simples (e não rx.code_block, que puxaria uma biblioteca JS nova).
            rx.box(
                rx.text(MODELO, white_space="pre-wrap", font_family="monospace", size="2"),
                padding="10px",
                border_radius="6px",
                background_color=rx.color("gray", 3),
                width="100%",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("copy", size=14),
                    "Copiar modelo",
                    on_click=rx.set_clipboard(MODELO),
                    variant="soft",
                    size="1",
                ),
                rx.button(
                    rx.icon("bot", size=14),
                    "Copiar prompt para IA",
                    on_click=ImportacaoState.copiar_prompt(False),
                    variant="soft",
                    size="1",
                ),
                rx.button(
                    rx.icon("bot", size=14),
                    "Copiar prompt com lista de setores",
                    on_click=ImportacaoState.copiar_prompt(True),
                    variant="soft",
                    size="1",
                ),
                spacing="2",
                wrap="wrap",
            ),
            spacing="2",
            align="start",
            width="100%",
        ),
        width="100%",
    )


def _linha_os(o) -> rx.Component:
    return rx.table.row(
        rx.table.cell(o.linha),
        rx.table.cell(rx.text(o.chamado, weight="bold")),
        rx.table.cell(o.setor),
        rx.table.cell(o.modalidade),
        rx.table.cell(o.descricao),
        rx.table.cell(o.responsavel),
        rx.table.cell(
            rx.cond(
                o.itens.length() > 0,
                rx.vstack(
                    rx.foreach(o.itens, lambda i: rx.text(i, size="1")),
                    spacing="1",
                    align="start",
                ),
                rx.text("—", color=rx.color("gray", 9)),
            )
        ),
    )


def _tabela_previa() -> rx.Component:
    return rx.vstack(
        rx.text(
            ImportacaoState.previa_os.length().to_string()
            + " O.S. serão criadas, com "
            + ImportacaoState.total_itens.to_string()
            + " item(ns):",
            size="2",
            weight="medium",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Linha"),
                    rx.table.column_header_cell("Chamado"),
                    rx.table.column_header_cell("Setor"),
                    rx.table.column_header_cell("Modalidade"),
                    rx.table.column_header_cell("Descrição"),
                    rx.table.column_header_cell("Responsável"),
                    rx.table.column_header_cell("Itens"),
                ),
            ),
            rx.table.body(rx.foreach(ImportacaoState.previa_os, _linha_os)),
            variant="surface",
            width="100%",
        ),
        spacing="2",
        align="start",
        width="100%",
    )


def _botao_sugestao(s) -> rx.Component:
    """Um clique troca o campo errado pelo nome do cadastro e analisa de novo."""
    return rx.button(
        s.campo + ": " + s.valor,
        on_click=ImportacaoState.aplicar_sugestao(s.linha, s.indice, s.valor),
        type="button",
        variant="soft",
        size="1",
    )


def _mensagem(m) -> rx.Component:
    return rx.vstack(
        rx.text("Linha " + m.linha.to_string() + ": " + m.mensagem, size="2"),
        rx.code(m.texto, size="1"),
        rx.cond(
            m.sugestoes.length() > 0,
            rx.vstack(
                rx.text("Quis dizer:", size="1"),
                rx.hstack(
                    rx.foreach(m.sugestoes, _botao_sugestao),
                    spacing="2",
                    wrap="wrap",
                ),
                spacing="1",
                align="start",
            ),
        ),
        spacing="1",
        align="start",
        width="100%",
    )


def _bloco_mensagens(titulo: str, lista, cor: str) -> rx.Component:
    return rx.cond(
        lista.length() > 0,
        rx.callout.root(
            rx.callout.icon(rx.icon("triangle-alert")),
            rx.callout.text(
                rx.vstack(
                    rx.text(titulo, weight="medium", size="2"),
                    rx.foreach(lista, _mensagem),
                    spacing="2",
                    align="start",
                    width="100%",
                )
            ),
            color_scheme=cor,
            width="100%",
        ),
    )


def _previa() -> rx.Component:
    return rx.cond(
        ImportacaoState.analisado,
        rx.vstack(
            _bloco_mensagens(
                "Linhas recusadas (não serão gravadas):", ImportacaoState.previa_erros, "red"
            ),
            _bloco_mensagens("Avisos:", ImportacaoState.previa_avisos, "amber"),
            rx.cond(
                ImportacaoState.previa_os.length() > 0,
                rx.vstack(
                    _tabela_previa(),
                    rx.button(
                        rx.icon("check", size=16),
                        "Gravar O.S.",
                        on_click=ImportacaoState.gravar,
                        size="3",
                    ),
                    spacing="4",
                    align="start",
                    width="100%",
                ),
                rx.text("Nenhuma O.S. válida no texto.", size="2"),
            ),
            spacing="4",
            align="start",
            width="100%",
        ),
    )


def ordens_importar_page() -> rx.Component:
    return page_layout(
        rx.hstack(
            rx.heading("Importar O.S. em lote", size="7"),
            rx.spacer(),
            rx.link(
                rx.button("Voltar", variant="soft", color_scheme="gray", size="3"),
                href="/ordens",
            ),
            width="100%",
            align="center",
        ),
        _ajuda(),
        rx.text_area(
            value=ImportacaoState.texto,
            on_change=ImportacaoState.set_texto,
            placeholder="Cole aqui a lista de O.S....",
            rows="12",
            width="100%",
            font_family="monospace",
        ),
        rx.cond(
            ImportacaoState.error_message != "",
            rx.text(ImportacaoState.error_message, color=rx.color("red", 10), size="2"),
        ),
        rx.cond(
            ImportacaoState.mensagem_sucesso != "",
            rx.callout.root(
                rx.callout.icon(rx.icon("circle-check")),
                rx.callout.text(ImportacaoState.mensagem_sucesso),
                color_scheme="green",
                width="100%",
            ),
        ),
        rx.hstack(
            rx.button(
                rx.icon("search", size=16),
                "Analisar",
                on_click=ImportacaoState.analisar,
                size="3",
            ),
            spacing="3",
        ),
        _previa(),
    )
