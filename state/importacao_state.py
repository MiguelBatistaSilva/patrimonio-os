"""Cérebro da tela de importação em lote (/ordens/importar).

Fluxo: o operador cola o texto -> "Analisar" mostra a pré-visualização (o que será
gravado e o que foi recusado, linha por linha) -> "Gravar" cria as O.S. válidas.

Detalhe de segurança: o "Gravar" NÃO reaproveita a análise anterior — ele lê o texto e
confere o cadastro de novo. Assim o que vai para o banco é sempre coerente com o que
está na caixa agora. E se o texto for editado depois de analisar, a pré-visualização
some (set_texto) e o botão de gravar com ela: ninguém grava algo que não viu.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

import reflex as rx

from crud import dominio as crud_dominio
from crud import ordem_servico as crud_os
from models.dominio import Classificacao, Meio, Modalidade, Peso, Setor
from services import importacao_lote as lote
from services.database import SessionLocal
from services.importacao_prompt import montar_prompt
from services.importacao_texto import interpretar, substituir_campo
from state.auth_state import AuthState

log = logging.getLogger(__name__)

# Exemplo mostrado na tela e copiado pelo botão "Copiar modelo".
MODELO = (
    "8500123-45.2026.8.06.0000;21° Vara Cível;Reparo;Notebook não liga;Maria\n"
    "item;123456;Notebook Dell Latitude\n"
    "item;;Monitor 22 polegadas\n"
    "8500456-78.2026.8.06.0000;Vara Única da Comarca de Milagres;Recolhimento;Recolher impressora sem uso;Carlos\n"
)


@dataclass
class LinhaPrevia:
    """Uma O.S. da pré-visualização, achatada para a tela (tudo texto)."""

    linha: int
    chamado: str
    setor: str
    modalidade: str
    descricao: str
    responsavel: str
    itens: list[str] = field(default_factory=list)


@dataclass
class SugestaoPrevia:
    """Um botão de correção: troca o campo `indice` da linha `linha` por `valor`."""

    linha: int
    indice: int
    campo: str
    valor: str


@dataclass
class MensagemPrevia:
    """Um erro ou aviso, com a linha original para o operador se localizar."""

    linha: int
    mensagem: str
    texto: str
    sugestoes: list[SugestaoPrevia] = field(default_factory=list)


class ImportacaoState(rx.State):
    texto: str = ""
    analisado: bool = False
    previa_os: list[LinhaPrevia] = []
    previa_erros: list[MensagemPrevia] = []
    previa_avisos: list[MensagemPrevia] = []
    mensagem_sucesso: str = ""
    error_message: str = ""

    @rx.var
    def total_itens(self) -> int:
        return sum(len(o.itens) for o in self.previa_os)

    def carregar(self):
        """on_load: abre a tela sempre limpa."""
        self.texto = ""
        self._limpar_previa()
        self.mensagem_sucesso = ""
        self.error_message = ""

    def set_texto(self, valor: str):
        self.texto = valor
        self._limpar_previa()  # texto mudou: a pré-visualização antiga não vale mais
        self.mensagem_sucesso = ""

    def _limpar_previa(self):
        self.analisado = False
        self.previa_os = []
        self.previa_erros = []
        self.previa_avisos = []
        self.error_message = ""

    # ── Consulta ao cadastro (uma sessão curta, só leitura) ──
    def _montar_previa(self) -> lote.Previa:
        lido = interpretar(self.texto)
        db = SessionLocal()
        try:
            pares_setor = [(r.nome, r.id) for r in crud_dominio.listar(db, Setor)]
            pares_modalidade = [(r.nome, r.id) for r in crud_dominio.listar(db, Modalidade)]
            existentes = crud_os.chamados_existentes(db, [o.chamado for o in lido.ordens])
        finally:
            db.close()
        return lote.resolver(
            lido,
            lote.indexar(pares_setor),
            lote.indexar(pares_modalidade),
            existentes,
            lote.nomes_por_chave([n for n, _ in pares_setor]),
            lote.nomes_por_chave([n for n, _ in pares_modalidade]),
        )

    def analisar(self):
        self._limpar_previa()
        self.mensagem_sucesso = ""
        if not self.texto.strip():
            self.error_message = "Cole o texto com as O.S. antes de analisar."
            return

        previa = self._montar_previa()
        self.previa_os = [
            LinhaPrevia(
                linha=o.linha,
                chamado=o.chamado,
                setor=o.setor,
                modalidade=o.modalidade,
                descricao=o.descricao,
                responsavel=o.responsavel or "—",
                itens=[
                    " — ".join(p for p in (i.tombo_ns, i.descricao) if p)
                    for i in o.itens
                ],
            )
            for o in previa.prontas
        ]
        self.previa_erros = [
            MensagemPrevia(
                linha=e.linha,
                mensagem=e.mensagem,
                texto=e.texto,
                sugestoes=[
                    SugestaoPrevia(e.linha, s.indice, s.campo, s.valor) for s in e.sugestoes
                ],
            )
            for e in sorted(previa.erros, key=lambda e: e.linha)
        ]
        self.previa_avisos = [
            MensagemPrevia(linha=a.linha, mensagem=a.mensagem, texto=a.texto)
            for a in sorted(previa.avisos, key=lambda a: a.linha)
        ]
        self.analisado = True

    def aplicar_sugestao(self, linha: int, indice: int, valor: str):
        """Clique numa sugestão: corrige o campo na caixa de texto e analisa de novo."""
        self.texto = substituir_campo(self.texto, linha, indice, valor)
        self.analisar()

    def copiar_prompt(self, com_setores: bool):
        """Copia para a área de transferência o prompt a colar numa IA de chat.

        Montado na hora com os cadastros atuais, para nunca ficar desatualizado."""
        db = SessionLocal()
        try:
            modalidades = [r.nome for r in crud_dominio.listar(db, Modalidade)]
            setores = [r.nome for r in crud_dominio.listar(db, Setor)] if com_setores else None
        finally:
            db.close()
        return [
            rx.set_clipboard(montar_prompt(modalidades, setores)),
            rx.toast.success("Prompt copiado. Cole na sua IA de chat."),
        ]

    async def gravar(self):
        self.error_message = ""
        self.mensagem_sucesso = ""

        previa = self._montar_previa()  # confere de novo — ver o docstring do módulo
        if not previa.prontas:
            self.error_message = "Não há nenhuma O.S. válida para gravar."
            return

        auth = await self.get_state(AuthState)
        agora = datetime.now()
        db = SessionLocal()
        try:
            def id_padrao(Model, nome: str):
                # Padrão do cadastro (Meio "Chamado" etc.); se não existir, fica vazio.
                return lote.indexar(
                    [(r.nome, r.id) for r in crud_dominio.listar(db, Model)]
                ).get(lote.normalizar(nome))

            padroes = {
                "meio_id": id_padrao(Meio, lote.MEIO_PADRAO),
                "classificacao_id": id_padrao(Classificacao, lote.CLASSIFICACAO_PADRAO),
                "peso_id": id_padrao(Peso, lote.PESO_PADRAO),
            }
            ordens = [
                {
                    "dados": {
                        "data_abertura": agora.date(),
                        "hora_abertura": agora.time().replace(second=0, microsecond=0),
                        "processo_chamado": o.chamado,
                        "responsavel": o.responsavel,
                        "descricao": o.descricao,
                        "modalidade_id": o.modalidade_id,
                        "setor_demandante_id": o.setor_id,
                        # A unidade que atende é o próprio setor que pediu.
                        "unidade_atendimento_id": o.setor_id,
                        **padroes,
                    },
                    "itens": [
                        {"tombo_ns": i.tombo_ns, "descricao": i.descricao} for i in o.itens
                    ],
                }
                for o in previa.prontas
            ]
            try:
                crud_os.criar_lote(db, int(auth.user_id), ordens)
            except Exception:
                log.exception("Falha ao gravar o lote de O.S.")
                self.error_message = (
                    "Não foi possível gravar. Nenhuma O.S. foi criada; tente de novo."
                )
                return
        finally:
            db.close()

        # O que foi gravado sai da caixa; o que foi recusado volta para ser corrigido.
        self.texto = previa.texto_dos_erros()
        self._limpar_previa()
        total = len(ordens)
        resto = len(previa.erros)
        self.mensagem_sucesso = f"{total} O.S. criada(s)." + (
            f" {resto} linha(s) recusada(s) voltaram para a caixa, para você corrigir."
            if resto
            else ""
        )
