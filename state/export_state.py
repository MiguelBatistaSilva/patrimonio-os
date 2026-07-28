"""Cérebro da exportação de O.S. para CSV.

State SEPARADO do OsState de propósito: o OsState é quem roda a lista, o formulário e
o detalhe — as telas que não podem quebrar. Mantendo a exportação aqui fora, um erro
neste arquivo não tem como derrubar aquelas telas.

Regra do período, igual à dos filtros da lista: campo de data em branco = SEM filtro.
Então "exportar tudo" é simplesmente não preencher nada.
"""

from datetime import date

import reflex as rx

from services.database import SessionLocal
from services import exportacao
from crud import ordem_servico as crud_os


class ExportState(rx.State):
    # Diálogo aberto/fechado (o item do menu só liga isto aqui).
    aberto: bool = False
    data_de: str = ""
    data_ate: str = ""
    erro: str = ""

    def ao_abrir(self, aberto: bool):
        """Chamado quando o diálogo abre ou fecha. Ao ABRIR, começa tudo limpo."""
        self.aberto = aberto
        self.erro = ""
        if aberto:
            self.data_de = ""
            self.data_ate = ""

    def abrir(self):
        """Ligado ao item 'Exportar dados (CSV)' do menu."""
        self.ao_abrir(True)

    def set_data_de(self, valor: str):
        self.data_de = valor
        self.erro = ""

    def set_data_ate(self, valor: str):
        self.data_ate = valor
        self.erro = ""

    def exportar(self):
        """Lê as O.S., monta o CSV e manda o navegador baixar."""
        self.erro = ""

        # Converte o que o usuário digitou. Vazio = None = sem filtro daquele lado.
        try:
            data_de = date.fromisoformat(self.data_de) if self.data_de else None
            data_ate = date.fromisoformat(self.data_ate) if self.data_ate else None
        except ValueError:
            self.erro = "Data em formato inválido."
            return

        if data_de and data_ate and data_de > data_ate:
            self.erro = "A data inicial não pode ser maior que a final."
            return

        db = SessionLocal()
        try:
            ordens = crud_os.listar_para_exportacao(db, data_de=data_de, data_ate=data_ate)
            if not ordens:
                # Sem isto, o chefe baixaria um arquivo só com o cabeçalho e acharia
                # que o sistema perdeu os dados.
                self.erro = "Nenhuma O.S. encontrada para exportar."
                return
            # Gera o arquivo AINDA com a sessão aberta: é aqui que os dados das tabelas
            # ligadas (modalidade, equipe, itens...) são realmente lidos.
            conteudo = exportacao.gerar_csv(ordens)
            quantidade = len(ordens)
        finally:
            db.close()

        self.aberto = False
        return [
            rx.download(
                data=conteudo,
                filename=exportacao.nome_arquivo(data_de, data_ate),
                mime_type="text/csv",
            ),
            rx.toast.success(f"{quantidade} O.S. exportadas."),
        ]
