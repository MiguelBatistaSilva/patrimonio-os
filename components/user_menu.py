"""Menu do usuário logado — fica no rodapé da sidebar.

Mostra o nome, abre um dropdown com Configurações, alternar tema claro/escuro e Sair.
Adapta-se ao estado colapsado/expandido da sidebar.

(Era uma classe só de @staticmethod no projeto antigo; aqui virou funções soltas — o
estilo idiomático que combinamos. As funções com "_" na frente são auxiliares internas.)
"""

import reflex as rx

from state.auth_state import AuthState
from state.export_state import ExportState
from state.sidebar_state import SidebarState


def _trigger() -> rx.Component:
    """O botão que abre o menu. Expandido mostra o nome; contraído, só o ícone."""
    return rx.button(
        rx.icon("circle-user", size=15, flex_shrink="0"),
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
        rx.dropdown_menu.item(
            rx.hstack(
                rx.icon("file-down", size=14),
                rx.text("Exportar dados (CSV)", size="2"),
                spacing="2",
                align="center",
            ),
            on_click=ExportState.abrir,
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


def _campo_data(label: str, valor, on_change) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.input(type="date", value=valor, on_change=on_change, width="100%"),
        spacing="1",
        align="start",
        width="100%",
    )


def _dialog_exportar() -> rx.Component:
    """Diálogo do CSV. Sem trigger: quem abre é o item do menu, mudando o state."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Exportar O.S. para CSV"),
            rx.dialog.description(
                "Gera uma planilha com uma linha por Ordem de Serviço. "
                "Deixe as datas em branco para exportar tudo.",
                size="2",
                color=rx.color("gray", 10),
            ),
            rx.vstack(
                rx.hstack(
                    _campo_data("De", ExportState.data_de, ExportState.set_data_de),
                    _campo_data("Até", ExportState.data_ate, ExportState.set_data_ate),
                    spacing="3",
                    width="100%",
                ),
                rx.text(
                    "O período considera a data de ABERTURA da O.S.",
                    size="1",
                    color=rx.color("gray", 10),
                ),
                rx.cond(
                    ExportState.erro != "",
                    rx.text(ExportState.erro, color=rx.color("red", 10), size="2"),
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button("Cancelar", variant="soft", color_scheme="gray"),
                    ),
                    rx.button(
                        rx.icon("download", size=16),
                        "Exportar",
                        on_click=ExportState.exportar,
                    ),
                    justify="end",
                    spacing="3",
                    width="100%",
                ),
                spacing="3",
                margin_top="12px",
            ),
            max_width="420px",
        ),
        open=ExportState.aberto,
        on_open_change=ExportState.ao_abrir,
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
        # O diálogo fica FORA do dropdown de propósito: ao clicar num item, o dropdown
        # se fecha e some da tela — levaria o diálogo junto antes de ele aparecer.
        _dialog_exportar(),
        width="100%",
        padding_top="4px",
        padding_bottom="8px",
        padding_x="8px",
    )
