"""Tela de detalhe de uma Ordem de Serviço.

Mostra todos os dados + a equipe (que até aqui estava gravada mas invisível) e oferece
o botão Imprimir. A URL é dinâmica: /ordens/<id> — o id é lido no carregar_detalhe.
"""

import reflex as rx

from components.layout import page_layout
from state.os_state import OsState
from state.auth_state import AuthState


def _info(label: str, valor) -> rx.Component:
    """Um par rótulo (pequeno, cinza) + valor."""
    return rx.vstack(
        rx.text(label, size="1", color=rx.color("gray", 10), weight="medium"),
        rx.text(valor, size="2"),
        spacing="0",
        align="start",
    )


def _campo_dlg(label: str, tipo: str, valor, on_change) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.input(type=tipo, value=valor, on_change=on_change, width="100%"),
        spacing="1",
        align="start",
        width="100%",
    )


def _dialog_concluir() -> rx.Component:
    """Diálogo onde o chefe transcreve a data/horas que vieram do papel."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(rx.icon("check", size=16), "Concluir", size="2"),
        ),
        rx.dialog.content(
            rx.dialog.title("Concluir Ordem de Serviço"),
            rx.dialog.description(
                "Transcreva o que veio no papel. As horas são opcionais.",
                size="2",
                color=rx.color("gray", 10),
            ),
            rx.vstack(
                _campo_dlg("Data de conclusão", "date", OsState.f_data_conclusao, OsState.set_f_data_conclusao),
                _campo_dlg("Hora inicial", "time", OsState.f_hora_inicial, OsState.set_f_hora_inicial),
                _campo_dlg("Hora final", "time", OsState.f_hora_final, OsState.set_f_hora_final),
                rx.cond(
                    OsState.error_message != "",
                    rx.text(OsState.error_message, color=rx.color("red", 10), size="2"),
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button("Cancelar", variant="soft", color_scheme="gray"),
                    ),
                    rx.button("Confirmar conclusão", on_click=OsState.concluir),
                    justify="end",
                    spacing="3",
                    width="100%",
                ),
                spacing="3",
                margin_top="12px",
            ),
            max_width="420px",
        ),
        open=OsState.dialog_concluir,
        on_open_change=OsState.ao_abrir_dialog,
    )


def _acoes_status(d) -> rx.Component:
    """Pendente: Concluir + Cancelar. Concluída/Cancelada: Reabrir."""
    return rx.cond(
        d.status == "Pendente",
        rx.hstack(
            _dialog_concluir(),
            rx.button(
                rx.icon("x", size=16),
                "Cancelar O.S.",
                on_click=OsState.cancelar,
                color_scheme="red",
                variant="soft",
                size="2",
            ),
            spacing="2",
        ),
        rx.button(
            rx.icon("rotate-ccw", size=16),
            "Reabrir",
            on_click=OsState.reabrir,
            variant="soft",
            size="2",
        ),
    )


def _detalhe() -> rx.Component:
    d = OsState.detalhe
    return rx.vstack(
        rx.hstack(
            rx.heading(d.numero, size="7"),
            rx.badge(d.status, size="2"),
            rx.spacer(),
            _acoes_status(d),
            # Editar: só admin vê (a rota também é travada por check_admin).
            rx.cond(
                AuthState.is_admin,
                rx.link(
                    rx.button(
                        rx.icon("pencil", size=16),
                        "Editar",
                        variant="soft",
                        size="2",
                    ),
                    href="/ordens/" + d.id.to_string() + "/editar",
                ),
            ),
            rx.link(
                rx.button(
                    rx.icon("printer", size=16),
                    "Imprimir",
                    variant="soft",
                    size="2",
                ),
                href="/ordens/" + d.id.to_string() + "/imprimir",
            ),
            width="100%",
            align="center",
            spacing="2",
        ),
        rx.divider(),
        rx.grid(
            _info("Abertura", d.data_abertura + " " + d.hora_abertura),
            _info("Operador", d.operador),
            _info("Modalidade", d.modalidade),
            _info("Classificação", d.classificacao),
            _info("Peso", d.peso),
            _info("Meio", d.meio),
            _info("Setor demandante", d.setor_demandante),
            _info("Unidade de atendimento", d.unidade_atendimento),
            _info("Tipo de veículo", d.tipo_veiculo),
            _info("Responsável", d.responsavel),
            _info("Contato", d.contato),
            _info("Processo / Chamado", d.processo_chamado),
            _info("Âmbito", d.ambito),
            _info("Autorizado por", d.autorizado_por),
            _info("Requer rota", rx.cond(d.requer_rota, "Sim", "Não")),
            _info("Data de conclusão", d.data_conclusao),
            _info("Hora inicial", d.hora_inicial),
            _info("Hora final", d.hora_final),
            columns="3",
            spacing="4",
            width="100%",
        ),
        _info("Endereço", d.endereco),
        _info("Descrição", d.descricao),
        rx.divider(),
        rx.text("Equipe", weight="medium", size="2"),
        rx.cond(
            d.equipe.length() > 0,
            rx.hstack(
                rx.foreach(d.equipe, lambda n: rx.badge(n, size="2")),
                wrap="wrap",
                spacing="2",
            ),
            rx.text("Sem equipe atribuída.", size="2", color=rx.color("gray", 10)),
        ),
        rx.divider(),
        rx.text("Itens", weight="medium", size="2"),
        rx.cond(
            d.itens.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Tombo ou N/S"),
                        rx.table.column_header_cell("Descrição"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        d.itens,
                        lambda it: rx.table.row(
                            rx.table.cell(it.tombo_ns),
                            rx.table.cell(it.descricao),
                        ),
                    ),
                ),
                variant="surface",
                width="100%",
            ),
            rx.text("Sem itens cadastrados.", size="2", color=rx.color("gray", 10)),
        ),
        spacing="4",
        width="100%",
        align="start",
    )


def ordem_detalhe_page() -> rx.Component:
    return page_layout(
        rx.link(
            rx.hstack(
                rx.icon("arrow-left", size=14),
                rx.text("Voltar para a lista"),
                spacing="1",
                align="center",
            ),
            href="/ordens",
            color=rx.color("gray", 11),
        ),
        rx.cond(
            OsState.encontrada,
            _detalhe(),
            rx.text("Ordem de Serviço não encontrada.", size="3"),
        ),
    )
