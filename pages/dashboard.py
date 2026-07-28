"""Dashboard — visão geral das Ordens de Serviço.

Filtro de período no topo, cartões de contagem, gráficos e a lista do que está parado.
Tudo é só leitura, carregado no on_load (ver app.py) e recarregado a cada filtro.

Por que os gráficos são feitos "na mão" com caixas e CSS, em vez de uma biblioteca de
gráficos? Porque uma biblioteca nova (recharts) precisaria ser BAIXADA do npm no
primeiro start — e a rede cabeada do fórum bloqueia isso. O app poderia simplesmente
não subir na máquina do chefe. Caixa com altura em porcentagem não depende de nada.
"""

import reflex as rx

from components.layout import page_layout
from state.auth_state import AuthState
from state.dashboard_state import DashboardState


# ── Peças ────────────────────────────────────────────────────────────────────────

def _card(label: str, valor, cor: str, sufixo: str = "") -> rx.Component:
    """Cartão de contador: rótulo pequeno + número grande colorido."""
    return rx.card(
        rx.vstack(
            rx.text(label, size="2", color=rx.color("gray", 10)),
            rx.hstack(
                rx.heading(valor, size="8", color=rx.color(cor, 11)),
                rx.cond(
                    sufixo != "",
                    rx.text(sufixo, size="2", color=rx.color("gray", 10)),
                ),
                spacing="2",
                align="baseline",
            ),
            spacing="1",
            align="start",
        ),
        width="100%",
    )


def _painel(titulo: str, conteudo: rx.Component, vazio: str, tem_dados) -> rx.Component:
    """Um bloco de gráfico com título e uma mensagem para quando não há o que mostrar."""
    return rx.card(
        rx.vstack(
            rx.text(titulo, size="2", weight="bold"),
            rx.divider(),
            rx.cond(
                tem_dados,
                conteudo,
                rx.text(vazio, size="2", color=rx.color("gray", 10)),
            ),
            spacing="3",
            width="100%",
            align="start",
        ),
        width="100%",
    )


def _barra(b) -> rx.Component:
    """Barra horizontal: nome + quantidade em cima, barra proporcional embaixo."""
    return rx.vstack(
        rx.hstack(
            # Nome de setor pode ser gigante ("Centro Judiciário de Solução de
            # Conflitos e Cidadania da Comarca de Tianguá"). flex+min_width=0 deixa o
            # texto encolher, e o ellipsis corta com "…" em vez de no seco.
            rx.text(
                b.nome,
                size="2",
                white_space="nowrap",
                overflow="hidden",
                text_overflow="ellipsis",
                flex="1",
                min_width="0",
            ),
            rx.text(b.qtd, size="2", weight="bold", flex_shrink="0"),
            spacing="2",
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


def _coluna(c) -> rx.Component:
    """Coluna vertical do gráfico de meses.

    A caixa de fora tem altura fixa e serve de "trilho"; a de dentro é ancorada no
    rodapé (position absolute + bottom 0) e cresce em porcentagem. min_height garante
    que um mês com pouquíssimas O.S. ainda apareça como um risquinho visível.
    """
    return rx.vstack(
        rx.text(c.qtd, size="1", weight="bold"),
        rx.box(
            rx.box(
                position="absolute",
                bottom="0",
                left="0",
                right="0",
                height=c.pct.to_string() + "%",
                min_height="3px",
                background_color=rx.color("accent", 9),
                border_radius="3px 3px 0 0",
            ),
            position="relative",
            width="100%",
            height="110px",
            background_color=rx.color("gray", 3),
            border_radius="3px",
        ),
        rx.text(c.rotulo, size="1", color=rx.color("gray", 10), white_space="nowrap"),
        spacing="1",
        align="center",
        flex="1",
        min_width="34px",
    )


def _linha_pendente(p) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.link(
                rx.text(p.numero, weight="bold", size="2"),
                href="/ordens/" + p.id.to_string(),
            ),
        ),
        rx.table.cell(rx.text(p.data_abertura, size="2")),
        rx.table.cell(rx.badge(p.dias.to_string() + " dias", color_scheme=p.cor)),
        rx.table.cell(rx.text(p.setor, size="2")),
        rx.table.cell(rx.text(p.modalidade, size="2")),
    )


def _filtros() -> rx.Component:
    """Período + atalhos. Datas em branco = desde sempre."""
    def campo(label: str, valor, on_change) -> rx.Component:
        return rx.vstack(
            rx.text(label, size="1", color=rx.color("gray", 10)),
            rx.input(type="date", value=valor, on_change=on_change),
            spacing="1",
            align="start",
        )

    def atalho(rotulo: str, on_click) -> rx.Component:
        return rx.button(rotulo, on_click=on_click, variant="soft", color_scheme="gray", size="2")

    return rx.hstack(
        campo("De", DashboardState.filtro_data_de, DashboardState.set_filtro_data_de),
        campo("Até", DashboardState.filtro_data_ate, DashboardState.set_filtro_data_ate),
        rx.hstack(
            atalho("Este mês", DashboardState.periodo_este_mes),
            atalho("Este ano", DashboardState.periodo_este_ano),
            atalho("Tudo", DashboardState.periodo_tudo),
            spacing="2",
        ),
        spacing="3",
        align="end",
        wrap="wrap",
        width="100%",
    )


# ── A página ─────────────────────────────────────────────────────────────────────

def dashboard_page() -> rx.Component:
    return page_layout(
        rx.heading("Dashboard", size="7"),
        rx.text("Bem-vindo, ", rx.text.strong(AuthState.nome), "!"),
        _filtros(),
        rx.cond(
            DashboardState.tem_filtro,
            rx.text(
                "Mostrando apenas as O.S. abertas no período selecionado.",
                size="1",
                color=rx.color("gray", 10),
            ),
        ),

        # ── Contadores ──
        rx.grid(
            _card("Total", DashboardState.total, "gray"),
            _card("Pendentes", DashboardState.pendentes, "amber"),
            _card("Concluídas", DashboardState.concluidas, "green"),
            _card("Canceladas", DashboardState.canceladas, "red"),
            columns="4",
            spacing="4",
            width="100%",
        ),
        rx.grid(
            _card("Tempo médio de conclusão", DashboardState.tempo_medio, "gray", "dias"),
            _card("Bens movimentados", DashboardState.itens_movimentados, "gray", "itens"),
            columns="2",
            spacing="4",
            width="100%",
        ),

        # ── Evolução no tempo ──
        _painel(
            "O.S. abertas por mês",
            rx.hstack(
                rx.foreach(DashboardState.por_mes, _coluna),
                spacing="2",
                width="100%",
                align="end",
            ),
            "Nenhuma O.S. no período.",
            DashboardState.por_mes.length() > 0,
        ),

        # ── Dois painéis lado a lado ──
        rx.grid(
            _painel(
                "Modalidades mais frequentes",
                rx.vstack(
                    rx.foreach(DashboardState.por_modalidade, _barra),
                    spacing="3",
                    width="100%",
                ),
                "Nenhuma O.S. com modalidade no período.",
                DashboardState.por_modalidade.length() > 0,
            ),
            _painel(
                "Atuação da equipe",
                rx.vstack(
                    rx.text(
                        "Em quantas O.S. cada um atuou. Uma O.S. com vários "
                        "operacionais conta para todos, então a soma passa do "
                        "total de O.S.",
                        size="1",
                        color=rx.color("gray", 10),
                    ),
                    rx.foreach(DashboardState.por_funcionario, _barra),
                    spacing="3",
                    width="100%",
                ),
                "Nenhuma equipe atribuída no período.",
                DashboardState.por_funcionario.length() > 0,
            ),
            columns="2",
            spacing="4",
            width="100%",
        ),

        # ── O que está parado ──
        _painel(
            "Pendentes há mais tempo",
            rx.vstack(
                rx.text(
                    "Independe do filtro de período — pendência antiga continua "
                    "sendo problema hoje.",
                    size="1",
                    color=rx.color("gray", 10),
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Número"),
                            rx.table.column_header_cell("Abertura"),
                            rx.table.column_header_cell("Parada há"),
                            rx.table.column_header_cell("Setor demandante"),
                            rx.table.column_header_cell("Modalidade"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(DashboardState.pendentes_antigas, _linha_pendente),
                    ),
                    variant="surface",
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            "Nenhuma O.S. pendente. Tudo em dia!",
            DashboardState.pendentes_antigas.length() > 0,
        ),
    )
