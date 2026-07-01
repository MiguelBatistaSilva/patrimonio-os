"""Layout de IMPRESSÃO de uma Ordem de Serviço.

Página dedicada (rota /ordens/[os_id]/imprimir) que NÃO usa o page_layout — ou seja,
não tem sidebar nem topbar. Renderiza só o "documento", para a impressão sair limpa.

Estrutura, espelhando o formulário oficial do Excel:
- 4 seções de DADOS (preenchidas com o que o sistema tem): Dados, Especificação do
  Atendimento, Atuação, Informações de Atendimento.  [agrupamento É UM PALPITE — ajustar]
- 3 seções EM BRANCO para o funcionário preencher à mão: Checklist, Itens, Resumo.
  Estas não vêm do banco — são espaço para escrever em campo.
"""

import reflex as rx

from state.os_state import OsState


# ── Peças reutilizáveis ─────────────────────────────────────────────────────────

def _campo(label: str, valor) -> rx.Component:
    """Par 'Rótulo: valor'. Campo vazio (placeholder '—') sai EM BRANCO no papel."""
    return rx.hstack(
        rx.text(f"{label}:", weight="bold", size="2", white_space="nowrap"),
        rx.text(rx.cond(valor == "—", "", valor), size="2"),
        spacing="1",
        align="start",
        width="100%",
    )


def _secao(titulo: str, *filhos: rx.Component) -> rx.Component:
    return rx.box(
        rx.text(
            titulo,
            weight="bold",
            size="2",
            border_bottom="1px solid black",
            padding_bottom="2px",
            margin_bottom="6px",
            width="100%",
        ),
        rx.vstack(*filhos, spacing="2", align="start", width="100%"),
        class_name="secao",  # CSS de impressão impede quebra de página no meio
        margin_bottom="16px",
        width="100%",
    )


def _check(label: str) -> rx.Component:
    """Item de checklist EM BRANCO: quadradinho + texto (para marcar à mão)."""
    return rx.hstack(
        rx.box(width="13px", height="13px", border="1.5px solid black", flex_shrink="0"),
        rx.text(label, size="2"),
        spacing="2",
        align="center",
    )


def _linha_branca(label: str) -> rx.Component:
    """Rótulo + linha em branco para escrever à mão."""
    return rx.hstack(
        rx.text(f"{label}:", weight="bold", size="2", white_space="nowrap"),
        rx.box(flex="1", border_bottom="1px solid black", height="18px"),
        spacing="2",
        align="end",
        width="100%",
    )


def _linha_item_vazia() -> rx.Component:
    return rx.table.row(
        rx.table.cell(" ", height="30px"),
        rx.table.cell(" "),
        rx.table.cell(" "),
        rx.table.cell(" "),
    )


# ── O documento ──────────────────────────────────────────────────────────────────

def _documento() -> rx.Component:
    d = OsState.detalhe
    return rx.vstack(
        # Cabeçalho institucional: brasão à esquerda + identificação ao lado.
        rx.hstack(
            rx.image(src="/brasao_ceara.svg", width="64px", height="auto"),
            rx.vstack(
                rx.text("ESTADO DO CEARÁ", weight="bold", size="2"),
                rx.text("PODER JUDICIÁRIO", weight="bold", size="2"),
                rx.text("FÓRUM CLÓVIS BEVILÁQUA", size="2"),
                rx.text("DIRETORIA ADMINISTRATIVA", size="2"),
                rx.text("SEÇÃO DE PATRIMÔNIO DA COMARCA DE FORTALEZA", size="2"),
                spacing="0",
                align="start",
            ),
            spacing="4",
            align="center",
            justify="center",
            width="100%",
        ),
        rx.heading("Nº " + d.numero, size="5"),
        rx.divider(border_color="black", margin_y="8px"),

        # ── Seções de DADOS (preenchidas) ──
        # Dados = quem SOLICITA o serviço.
        _secao(
            "Dados",
            rx.grid(
                _campo("Data de abertura", d.data_abertura),
                _campo("Hora de abertura", d.hora_abertura),
                _campo("Meio", d.meio),
                _campo("Processo / Chamado", d.processo_chamado),
                _campo("Responsável", d.responsavel),
                _campo("Contato", d.contato),
                _campo("Setor demandante", d.setor_demandante),
                columns="2",
                spacing="2",
                width="100%",
            ),
        ),
        _secao(
            "Especificação do Atendimento",
            rx.grid(
                _campo("Unidade de atendimento", d.unidade_atendimento),
                _campo("Âmbito", d.ambito),
                _campo("Requer rota", rx.cond(d.requer_rota, "Sim", "Não")),
                _campo("Classificação", d.classificacao),
                _campo("Modalidade", d.modalidade),
                _campo("Tipo de veículo", d.tipo_veiculo),  # provisório — confirmar seção
                columns="2",
                spacing="2",
                width="100%",
            ),
            _campo("Endereço", d.endereco),
            _campo("Causa", d.causa),
        ),
        # Atuação = quem ABRE a ordem de serviço.
        _secao(
            "Atuação",
            _campo("Descrição", d.descricao),
            _campo("Peso", d.peso),
            rx.grid(
                _campo("Autorização", d.autorizado_por),
                _campo("Operador", d.operador),
                columns="2",
                spacing="2",
                width="100%",
            ),
        ),
        _secao(
            "Informações de Atendimento",
            rx.hstack(
                rx.text("Operacional responsável:", weight="bold", size="2"),
                rx.cond(
                    d.equipe.length() > 0,
                    rx.hstack(
                        rx.foreach(d.equipe, lambda n: rx.text(n, size="2")),
                        spacing="3",
                        wrap="wrap",
                    ),
                    rx.text("", size="2"),
                ),
                spacing="2",
                align="start",
                wrap="wrap",
                width="100%",
            ),
            rx.grid(
                _campo("Data de conclusão", d.data_conclusao),
                _campo("Hora inicial", d.hora_inicial),
                _campo("Hora final", d.hora_final),
                _campo("Status", d.status),
                columns="2",
                spacing="2",
                width="100%",
            ),
        ),

        # ── Seções EM BRANCO (preencher à mão) ──
        _secao(
            "Checklist",
            _check("Preenchimento da ordem de serviço"),
            _check("Preenchimento do termo"),
            _check("Confirmação de movimentação no sistema"),
            _check("Atendimento da ordem de serviço"),
            rx.box(height="6px"),
            rx.hstack(
                rx.box(_linha_branca("Conferida e arquivada por"), flex="2"),
                rx.box(_linha_branca("Em"), flex="1"),
                spacing="4",
                width="100%",
                align="end",
            ),
        ),
        _secao(
            "Itens",
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Tombo ou N/S"),
                        rx.table.column_header_cell("Descrição"),
                        rx.table.column_header_cell("Origem"),
                        rx.table.column_header_cell("Destino"),
                    ),
                ),
                rx.table.body(*[_linha_item_vazia() for _ in range(10)]),
                variant="surface",
                width="100%",
            ),
        ),
        _secao(
            "Resumo da Ordem de Serviço",
            rx.grid(
                _campo("Número", d.numero),
                _campo("Unidade de atendimento", d.unidade_atendimento),
                _campo("Classificação", d.classificacao),
                _campo("Modalidade", d.modalidade),
                columns="2",
                spacing="2",
                width="100%",
            ),
            _campo("Descrição", d.descricao),
        ),
        spacing="2",
        align="start",
        width="100%",
    )


def ordem_print_page() -> rx.Component:
    return rx.box(
        # Barra de ações — NÃO sai na impressão (class_name="no-print").
        rx.hstack(
            rx.link(
                rx.button(
                    rx.icon("arrow-left", size=14),
                    "Voltar",
                    variant="soft",
                    color_scheme="gray",
                ),
                href="/ordens/" + OsState.detalhe.id.to_string(),
            ),
            rx.button(
                rx.icon("printer", size=16),
                "Imprimir",
                on_click=rx.call_script("window.print()"),
            ),
            spacing="3",
            padding="16px",
            class_name="no-print",
        ),
        rx.cond(
            OsState.encontrada,
            rx.center(
                rx.box(
                    _documento(),
                    class_name="documento",
                    background_color="white",
                    color="black",
                    padding="32px",
                    width="820px",
                    max_width="100%",
                    box_shadow="0 0 0 1px #ddd",
                ),
                width="100%",
                padding_bottom="40px",
            ),
            rx.center(rx.text("Ordem de Serviço não encontrada."), padding="40px"),
        ),
        min_height="100vh",
        width="100%",
        background_color=rx.color("gray", 3),
    )
