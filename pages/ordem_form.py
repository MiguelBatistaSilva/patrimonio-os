"""Formulário de nova Ordem de Serviço.

Usa rx.form com campos NOMEADOS (name="..."). No envio, on_submit=OsState.criar recebe
um dicionário com todos os campos de uma vez — sem precisar amarrar cada um a uma
variável de state. O número da O.S. NÃO está aqui: é gerado automaticamente ao salvar.
"""

import reflex as rx

from components.layout import page_layout
from state.os_state import OsState


def _campo(label: str, name: str, **input_props) -> rx.Component:
    """Rótulo + input de texto (ou date/time, via input_props)."""
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.input(name=name, width="100%", **input_props),
        spacing="1",
        align="start",
        width="100%",
    )


def _select(label: str, name: str, opcoes) -> rx.Component:
    """Rótulo + dropdown. As opções vêm do state (carregadas do banco)."""
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Selecione...", width="100%"),
            rx.select.content(
                rx.foreach(
                    opcoes,
                    lambda o: rx.select.item(o.nome, value=o.valor),
                ),
            ),
            name=name,
        ),
        spacing="1",
        align="start",
        width="100%",
    )


def _area(label: str, name: str) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.text_area(name=name, width="100%", rows="3"),
        spacing="1",
        align="start",
        width="100%",
    )


def _equipe() -> rx.Component:
    """Seção da equipe: 'Selecionar todos' + uma checkbox por funcionário ativo.

    Estas checkboxes NÃO usam name= (não vão no form_data): são controladas pelo state
    (equipe_selecionada), porque a lógica de marcar/desmarcar e 'todos' mora lá.
    """
    return rx.vstack(
        rx.text("Equipe", size="2", weight="medium"),
        rx.checkbox(
            "Selecionar todos",
            checked=OsState.todos_selecionados,
            on_change=OsState.alternar_todos,
            weight="medium",
        ),
        rx.divider(),
        rx.cond(
            OsState.funcionarios.length() > 0,
            rx.grid(
                rx.foreach(
                    OsState.funcionarios,
                    lambda f: rx.checkbox(
                        f.nome,
                        checked=OsState.equipe_selecionada.contains(f.valor),
                        on_change=OsState.alternar_funcionario(f.valor),
                    ),
                ),
                columns="3",
                spacing="3",
                width="100%",
            ),
            rx.text(
                "Nenhum funcionário cadastrado. Cadastre em Cadastros → Funcionários.",
                size="2",
                color=rx.color("gray", 10),
            ),
        ),
        spacing="2",
        align="start",
        width="100%",
    )


def ordem_form_page() -> rx.Component:
    return page_layout(
        rx.heading("Nova Ordem de Serviço", size="7"),
        rx.text(
            "O número é gerado automaticamente ao salvar. (* campos obrigatórios)",
            color=rx.color("gray", 10),
        ),
        rx.form.root(
            rx.vstack(
                rx.grid(
                    _campo("Data de abertura *", "data_abertura", type="date"),
                    _campo("Hora de abertura *", "hora_abertura", type="time"),
                    _select("Modalidade", "modalidade_id", OsState.opts_modalidade),
                    _select("Classificação", "classificacao_id", OsState.opts_classificacao),
                    _select("Peso", "peso_id", OsState.opts_peso),
                    _select("Meio", "meio_id", OsState.opts_meio),
                    _select("Setor demandante", "setor_demandante_id", OsState.opts_setor),
                    _select("Unidade de atendimento", "unidade_atendimento_id", OsState.opts_setor),
                    _select("Tipo de veículo", "tipo_veiculo_id", OsState.opts_tipo_veiculo),
                    _campo("Responsável", "responsavel"),
                    _campo("Contato", "contato"),
                    _campo("Processo / Chamado", "processo_chamado"),
                    _campo("Âmbito", "ambito"),
                    _campo("Autorizado por", "autorizado_por"),
                    columns="3",
                    spacing="4",
                    width="100%",
                ),
                _campo("Endereço", "endereco"),
                _area("Causa", "causa"),
                _area("Descrição", "descricao"),
                rx.checkbox("Requer rota", name="requer_rota"),
                _equipe(),
                rx.cond(
                    OsState.error_message != "",
                    rx.text(OsState.error_message, color=rx.color("red", 10), size="2"),
                ),
                rx.hstack(
                    rx.link(
                        rx.button(
                            "Cancelar",
                            type="button",
                            variant="soft",
                            color_scheme="gray",
                            size="3",
                        ),
                        href="/ordens",
                    ),
                    rx.button("Salvar O.S.", type="submit", size="3"),
                    spacing="3",
                ),
                spacing="5",
                width="100%",
                align="start",
            ),
            on_submit=OsState.criar,
            reset_on_submit=False,
            width="100%",
        ),
    )
