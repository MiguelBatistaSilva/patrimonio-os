"""Menu do usuário logado — fica no rodapé da sidebar.

Mostra o nome, abre um dropdown com Configurações, alternar tema claro/escuro e Sair.
Adapta-se ao estado colapsado/expandido da sidebar.

(Era uma classe só de @staticmethod no projeto antigo; aqui virou funções soltas — o
estilo idiomático que combinamos. As funções com "_" na frente são auxiliares internas.)
"""

import reflex as rx

from state.auth_state import AuthState
from state.catinet_state import ConfiguracoesState, CredenciaisState
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
        rx.cond(
            ~AuthState.is_visualizador,
            rx.dropdown_menu.item(
                rx.hstack(
                    rx.icon("settings", size=14),
                    rx.text("Configurações", size="2"),
                    spacing="2",
                    align="center",
                ),
                on_click=ConfiguracoesState.abrir,
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
        rx.cond(
            ~AuthState.is_visualizador,
            rx.dropdown_menu.item(
                rx.hstack(
                    rx.icon("key-round", size=14),
                    rx.text("Credenciais", size="2"),
                    spacing="2",
                    align="center",
                ),
                on_click=CredenciaisState.abrir,
            ),
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


def _campo_texto(label: str, valor, on_change, **props) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.input(value=valor, on_change=on_change, width="100%", **props),
        spacing="1",
        align="start",
        width="100%",
    )


def _dialog_credenciais() -> rx.Component:
    """Diálogo das credenciais do CATINET. A senha vai para o cofre do Windows."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Credenciais"),
            rx.dialog.description(
                "Usuário e senha do CATINET, usados pelo Pipeline de Dados. A senha fica "
                "guardada no cofre do Windows desta máquina, não no banco de dados.",
                size="2",
                color=rx.color("gray", 10),
            ),
            rx.vstack(
                _campo_texto(
                    "Usuário", CredenciaisState.usuario, CredenciaisState.set_usuario
                ),
                _campo_texto(
                    "Senha",
                    CredenciaisState.senha,
                    CredenciaisState.set_senha,
                    type="password",
                    placeholder=rx.cond(
                        CredenciaisState.tem_senha_salva,
                        "Já salva — deixe em branco para manter",
                        "",
                    ),
                ),
                rx.cond(
                    CredenciaisState.erro != "",
                    rx.text(CredenciaisState.erro, color=rx.color("red", 10), size="2"),
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button("Cancelar", variant="soft", color_scheme="gray"),
                    ),
                    rx.button(
                        rx.icon("save", size=16),
                        "Salvar",
                        on_click=CredenciaisState.salvar,
                    ),
                    justify="end",
                    spacing="3",
                    width="100%",
                ),
                spacing="3",
                margin_top="12px",
            ),
            max_width="460px",
        ),
        open=CredenciaisState.aberto,
        on_open_change=CredenciaisState.ao_abrir,
    )


def _dialog_configuracoes() -> rx.Component:
    """Diálogo de Configurações: por enquanto, só o link da fila do CATINET."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Configurações"),
            rx.dialog.description(
                "Endereço da fila do CATINET de onde o Pipeline de Dados lê os chamados "
                "(abra a fila no navegador e copie o endereço inteiro) e a frequência "
                "da busca automática.",
                size="2",
                color=rx.color("gray", 10),
            ),
            rx.vstack(
                _campo_texto(
                    "Link da fila do CATINET",
                    ConfiguracoesState.url_fila,
                    ConfiguracoesState.set_url_fila,
                    placeholder="https://.../assystnet/#eventMonitor/NÚMERO",
                ),
                rx.hstack(
                    rx.switch(
                        checked=ConfiguracoesState.auto_ligado,
                        on_change=ConfiguracoesState.set_auto_ligado,
                    ),
                    rx.text("Buscar chamados automaticamente", size="2"),
                    spacing="2",
                    align="center",
                ),
                _campo_texto(
                    "Intervalo da busca automática (minutos)",
                    ConfiguracoesState.intervalo,
                    ConfiguracoesState.set_intervalo,
                    type="number",
                    disabled=~ConfiguracoesState.auto_ligado,
                ),
                rx.cond(
                    ConfiguracoesState.erro != "",
                    rx.text(ConfiguracoesState.erro, color=rx.color("red", 10), size="2"),
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button("Cancelar", variant="soft", color_scheme="gray"),
                    ),
                    rx.button(
                        rx.icon("save", size=16),
                        "Salvar",
                        on_click=ConfiguracoesState.salvar,
                    ),
                    justify="end",
                    spacing="3",
                    width="100%",
                ),
                spacing="3",
                margin_top="12px",
            ),
            max_width="460px",
        ),
        open=ConfiguracoesState.aberto,
        on_open_change=ConfiguracoesState.ao_abrir,
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
        _dialog_credenciais(),
        _dialog_configuracoes(),
        width="100%",
        padding_top="4px",
        padding_bottom="8px",
        padding_x="8px",
    )
