"""Formulário de nova Ordem de Serviço.

Usa rx.form com campos NOMEADOS (name="..."). No envio, on_submit=OsState.criar recebe
um dicionário com todos os campos de uma vez — sem precisar amarrar cada um a uma
variável de state. O número da O.S. NÃO está aqui: é gerado automaticamente ao salvar.
"""

import reflex as rx

from components.layout import page_layout
from state.os_state import OsState


def _campo(label: str, name: str, **input_props) -> rx.Component:
    """Rótulo + input de texto (ou date/time, via input_props).

    default_value vem do state (form_inicial): em branco na criação, preenchido na
    edição. É "não controlado" — o valor final volta pelo form_data (name=), como antes.
    """
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.input(
            name=name,
            default_value=OsState.form_inicial[name],
            width="100%",
            **input_props,
        ),
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
            default_value=OsState.form_inicial[name],
        ),
        spacing="1",
        align="start",
        width="100%",
    )


def _area(label: str, name: str) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.text_area(
            name=name,
            default_value=OsState.form_inicial[name],
            width="100%",
            rows="3",
        ),
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


def _linha_item(item, idx) -> rx.Component:
    """Uma linha editável de item: 2 campos de texto + botão de remover.

    Igual às checkboxes da equipe, estes inputs NÃO usam name= — são controlados pelo
    state (itens_form). Cada tecla dispara set_item_campo(idx, campo, valor).
    """

    def campo(nome: str, placeholder: str) -> rx.Component:
        return rx.input(
            value=item[nome],
            on_change=lambda v: OsState.set_item_campo(idx, nome, v),
            placeholder=placeholder,
            width="100%",
        )

    # Só Tombo/N/S e Descrição (o bem movimentado). Origem/Destino continuam existindo
    # no model (sempre nulos), mas saíram do formulário, do detalhe e da impressão.
    return rx.hstack(
        campo("tombo_ns", "Tombo ou N/S"),
        campo("descricao", "Descrição (bem movimentado)"),
        rx.icon_button(
            rx.icon("trash-2", size=16),
            on_click=OsState.remover_item(idx),
            type="button",
            color_scheme="red",
            variant="soft",
        ),
        spacing="2",
        width="100%",
        align="center",
    )


def _itens() -> rx.Component:
    """Seção de Itens: uma linha por bem. Opcional — a O.S. pode nascer sem nenhum item."""
    return rx.vstack(
        rx.text("Itens", size="2", weight="medium"),
        rx.text(
            "Bens movimentados/atendidos nesta O.S. Opcional — adicione uma linha por item.",
            size="1",
            color=rx.color("gray", 10),
        ),
        rx.cond(
            OsState.itens_form.length() > 0,
            rx.vstack(
                rx.foreach(OsState.itens_form, _linha_item),
                spacing="2",
                width="100%",
            ),
        ),
        rx.button(
            rx.icon("plus", size=16),
            "Adicionar item",
            on_click=OsState.adicionar_item,
            type="button",
            variant="soft",
            size="2",
        ),
        spacing="2",
        align="start",
        width="100%",
    )


def ordem_form_page() -> rx.Component:
    return page_layout(
        rx.heading(
            rx.cond(OsState.editando_id != 0, "Editar Ordem de Serviço", "Nova Ordem de Serviço"),
            size="7",
        ),
        rx.text(
            rx.cond(
                OsState.editando_id != 0,
                "Corrija os dados e salve. O número e o operador não mudam. (* campos obrigatórios)",
                "O número é gerado automaticamente ao salvar. (* campos obrigatórios)",
            ),
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
                _area("Descrição", "descricao"),
                _itens(),
                rx.checkbox(
                    "Requer rota",
                    name="requer_rota",
                    default_checked=OsState.form_requer_rota,
                ),
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
            on_submit=OsState.salvar,
            reset_on_submit=False,
            width="100%",
        ),
    )
