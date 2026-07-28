"""Cérebro do Dashboard — só leitura.

Quem faz o trabalho pesado é o banco (COUNT/GROUP BY/AVG no crud); aqui a gente só
recebe os números prontos, formata para leitura humana e calcula a largura/altura das
barrinhas para a tela.

Tudo respeita um PERÍODO opcional (sobre a data de abertura). Campo em branco = sem
filtro, mesma regra dos filtros da lista de O.S. e da exportação.
"""

from dataclasses import dataclass
from datetime import date

import reflex as rx

from services.database import SessionLocal
from crud import ordem_servico as crud_os

MESES_CURTOS = (
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
)

# Quantos meses o gráfico de evolução mostra quando não há filtro de período.
MESES_NO_GRAFICO = 12


@dataclass
class Barra:
    """Uma linha do gráfico de barras horizontais: nome, quantidade e largura (%)."""

    nome: str
    qtd: int
    pct: int


@dataclass
class Coluna:
    """Uma coluna do gráfico de meses: rótulo ("jul/26"), quantidade e altura (%)."""

    rotulo: str
    qtd: int
    pct: int


@dataclass
class Pendente:
    """Uma O.S. pendente parada há muito tempo."""

    id: int
    numero: str
    data_abertura: str
    dias: int
    setor: str
    modalidade: str
    cor: str  # cor do badge de dias, decidida aqui no Python (ver _cor_por_dias)


def _barras(linhas: list[tuple[str, int]]) -> list[Barra]:
    """Transforma [(nome, qtd)] em barras. A maior vira 100%; as outras, proporcionais."""
    maior = max((qtd for _, qtd in linhas), default=0)
    return [
        Barra(nome=nome, qtd=qtd, pct=int(qtd * 100 / maior) if maior else 0)
        for nome, qtd in linhas
    ]


def _cor_por_dias(dias: int) -> str:
    """Semáforo da espera: até uma semana tudo bem, até um mês atenção, acima disso urgente."""
    if dias > 30:
        return "red"
    if dias > 7:
        return "amber"
    return "gray"


class DashboardState(rx.State):
    # Filtro de período (texto do <input type="date">; vazio = sem filtro).
    filtro_data_de: str = ""
    filtro_data_ate: str = ""

    # Cartões de contagem.
    total: int = 0
    pendentes: int = 0
    concluidas: int = 0
    canceladas: int = 0
    tempo_medio: str = "—"
    itens_movimentados: int = 0

    # Gráficos.
    por_mes: list[Coluna] = []
    por_modalidade: list[Barra] = []
    por_funcionario: list[Barra] = []

    # Lista de acompanhamento.
    pendentes_antigas: list[Pendente] = []

    # ── Filtro ──
    def set_filtro_data_de(self, valor: str):
        self.filtro_data_de = valor
        self.carregar()

    def set_filtro_data_ate(self, valor: str):
        self.filtro_data_ate = valor
        self.carregar()

    def periodo_este_mes(self):
        hoje = date.today()
        self.filtro_data_de = hoje.replace(day=1).isoformat()
        self.filtro_data_ate = hoje.isoformat()
        self.carregar()

    def periodo_este_ano(self):
        hoje = date.today()
        self.filtro_data_de = date(hoje.year, 1, 1).isoformat()
        self.filtro_data_ate = hoje.isoformat()
        self.carregar()

    def periodo_tudo(self):
        self.filtro_data_de = ""
        self.filtro_data_ate = ""
        self.carregar()

    @rx.var
    def tem_filtro(self) -> bool:
        return bool(self.filtro_data_de or self.filtro_data_ate)

    # ── Carga dos dados ──
    def carregar(self):
        """on_load da página e recarga a cada mudança de filtro."""
        # Data inválida (o usuário ainda está digitando) não pode derrubar a tela:
        # tratamos como "sem filtro" em vez de estourar.
        try:
            data_de = date.fromisoformat(self.filtro_data_de) if self.filtro_data_de else None
            data_ate = date.fromisoformat(self.filtro_data_ate) if self.filtro_data_ate else None
        except ValueError:
            data_de = data_ate = None

        db = SessionLocal()
        try:
            status = crud_os.contagem_por_status(db, data_de, data_ate)
            self.pendentes = status.get("Pendente", 0)
            self.concluidas = status.get("Concluída", 0)
            self.canceladas = status.get("Cancelada", 0)
            self.total = self.pendentes + self.concluidas + self.canceladas

            media = crud_os.tempo_medio_conclusao(db, data_de, data_ate)
            # Vírgula decimal (padrão brasileiro). Sem O.S. concluída, não há média.
            self.tempo_medio = f"{media:.1f}".replace(".", ",") if media is not None else "—"

            self.itens_movimentados = crud_os.total_itens(db, data_de, data_ate)

            self.por_mes = self._montar_meses(
                crud_os.contagem_por_mes(db, data_de, data_ate)
            )
            self.por_modalidade = _barras(
                crud_os.contagem_por_modalidade(db, data_de, data_ate)
            )
            self.por_funcionario = _barras(
                crud_os.contagem_por_funcionario(db, data_de, data_ate)
            )

            self.pendentes_antigas = [
                self._montar_pendente(o) for o in crud_os.pendentes_mais_antigas(db)
            ]
        finally:
            db.close()

    @staticmethod
    def _montar_pendente(o) -> Pendente:
        """Uma O.S. pendente vira uma linha da tabela de acompanhamento.

        `max(..., 0)`: se alguém digitar por engano uma data de abertura no futuro,
        a conta daria dias NEGATIVOS e a tela mostraria "-3 dias parada". Piso em zero.
        """
        dias = max((date.today() - o.data_abertura).days, 0)
        return Pendente(
            id=o.id,
            numero=o.numero,
            data_abertura=o.data_abertura.strftime("%d/%m/%Y"),
            dias=dias,
            setor=o.setor_demandante.nome if o.setor_demandante else "—",
            modalidade=o.modalidade.nome if o.modalidade else "—",
            cor=_cor_por_dias(dias),
        )

    @staticmethod
    def _montar_meses(linhas: list[tuple[int, int, int]]) -> list[Coluna]:
        """[(ano, mês, qtd)] vira colunas com rótulo "jul/26" e altura proporcional.

        Sem filtro de período, a lista pode cobrir anos inteiros e o gráfico ficaria
        ilegível — então mostramos só os últimos meses.
        """
        recentes = linhas[-MESES_NO_GRAFICO:]
        maior = max((qtd for _, _, qtd in recentes), default=0)
        return [
            Coluna(
                rotulo=f"{MESES_CURTOS[mes - 1]}/{ano % 100:02d}",
                qtd=qtd,
                pct=int(qtd * 100 / maior) if maior else 0,
            )
            for ano, mes, qtd in recentes
        ]
