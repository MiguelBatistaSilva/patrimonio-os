"""Cérebro do Dashboard — só leitura (contadores e visão por modalidade).

Quem faz o trabalho pesado é o banco (COUNT/GROUP BY no crud); aqui a gente só pega
os números prontos e calcula a largura das barrinhas para a tela.
"""

from dataclasses import dataclass

import reflex as rx

from services.database import SessionLocal
from crud import ordem_servico as crud_os


@dataclass
class BarraModalidade:
    """Uma linha do gráfico de barras: nome, quantidade e largura (%) da barra."""

    nome: str
    qtd: int
    pct: int


class DashboardState(rx.State):
    total: int = 0
    pendentes: int = 0
    concluidas: int = 0
    canceladas: int = 0
    por_modalidade: list[BarraModalidade] = []

    def carregar(self):
        db = SessionLocal()
        try:
            status = crud_os.contagem_por_status(db)
            self.pendentes = status.get("Pendente", 0)
            self.concluidas = status.get("Concluída", 0)
            self.canceladas = status.get("Cancelada", 0)
            self.total = self.pendentes + self.concluidas + self.canceladas

            modalidades = crud_os.contagem_por_modalidade(db)
            # A maior quantidade vira 100% de largura; as outras, proporcionais a ela.
            maior = max((qtd for _, qtd in modalidades), default=0)
            self.por_modalidade = [
                BarraModalidade(
                    nome=nome,
                    qtd=qtd,
                    pct=int(qtd * 100 / maior) if maior else 0,
                )
                for nome, qtd in modalidades
            ]
        finally:
            db.close()
