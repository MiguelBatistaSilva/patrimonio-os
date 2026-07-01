"""Cérebro das telas de Ordem de Serviço (lista + criação).

Note a diferença para o login: aqui o formulário é grande, então NÃO amarramos cada
campo a uma variável. Usamos rx.form com campos nomeados (name="..."); no envio, o
Reflex entrega tudo num dicionário (form_data) que este state lê de uma vez.
"""

from dataclasses import dataclass, field
from datetime import date, time

import reflex as rx

from services.database import SessionLocal
from crud import ordem_servico as crud_os
from crud import dominio as crud_dominio
from models.dominio import (
    Meio,
    Classificacao,
    Peso,
    TipoVeiculo,
    Modalidade,
    Setor,
)
from models.funcionario import Funcionario
from state.auth_state import AuthState


@dataclass
class OpcaoSelect:
    """Uma opção de dropdown. O <select> trabalha com texto, então o id vai como string."""

    valor: str
    nome: str


@dataclass
class LinhaOS:
    """Versão leve de uma O.S. para a tabela da listagem."""

    id: int
    numero: str
    data_abertura: str
    modalidade: str
    status: str


@dataclass
class DetalheOS:
    """Todos os dados de uma O.S., já "achatados" para a tela de detalhe.

    Os nomes das FKs (modalidade, setor...) já vêm resolvidos como texto, e a equipe
    como lista de nomes. Todos os campos têm default, então DetalheOS() cria um vazio —
    útil como valor inicial (evita lidar com None na tela).
    """

    id: int = 0
    numero: str = ""
    status: str = ""
    data_abertura: str = ""
    hora_abertura: str = ""
    operador: str = "—"
    modalidade: str = "—"
    classificacao: str = "—"
    peso: str = "—"
    meio: str = "—"
    setor_demandante: str = "—"
    unidade_atendimento: str = "—"
    tipo_veiculo: str = "—"
    requer_rota: bool = False
    processo_chamado: str = "—"
    responsavel: str = "—"
    contato: str = "—"
    ambito: str = "—"
    endereco: str = "—"
    causa: str = "—"
    descricao: str = "—"
    autorizado_por: str = "—"
    data_conclusao: str = "—"
    hora_inicial: str = "—"
    hora_final: str = "—"
    equipe: list[str] = field(default_factory=list)


class OsState(rx.State):
    ordens: list[LinhaOS] = []
    error_message: str = ""

    # Filtros da lista. "todos"/"todas" são sentinelas = sem filtro (o <select> não
    # aceita valor vazio, então usamos uma palavra-código que viramos None na consulta).
    filtro_status: str = "todos"
    filtro_modalidade: str = "todas"
    filtro_data_de: str = ""
    filtro_data_ate: str = ""

    # Cada setter atualiza o filtro e já recarrega a lista (filtra "ao vivo").
    def set_filtro_status(self, value: str):
        self.filtro_status = value
        self.carregar_lista()

    def set_filtro_modalidade(self, value: str):
        self.filtro_modalidade = value
        self.carregar_lista()

    def set_filtro_data_de(self, value: str):
        self.filtro_data_de = value
        self.carregar_lista()

    def set_filtro_data_ate(self, value: str):
        self.filtro_data_ate = value
        self.carregar_lista()

    def limpar_filtros(self):
        self.filtro_status = "todos"
        self.filtro_modalidade = "todas"
        self.filtro_data_de = ""
        self.filtro_data_ate = ""
        self.carregar_lista()

    # Detalhe de uma O.S. (tela /ordens/[os_id]).
    detalhe: DetalheOS = DetalheOS()
    encontrada: bool = False

    # Diálogo de conclusão (onde o chefe transcreve o que veio no papel).
    dialog_concluir: bool = False
    f_data_conclusao: str = ""
    f_hora_inicial: str = ""
    f_hora_final: str = ""

    def set_f_data_conclusao(self, value: str):
        self.f_data_conclusao = value

    def set_f_hora_inicial(self, value: str):
        self.f_hora_inicial = value

    def set_f_hora_final(self, value: str):
        self.f_hora_final = value

    # Opções dos dropdowns (carregadas do banco ao abrir o formulário).
    opts_meio: list[OpcaoSelect] = []
    opts_setor: list[OpcaoSelect] = []
    opts_tipo_veiculo: list[OpcaoSelect] = []
    opts_classificacao: list[OpcaoSelect] = []
    opts_modalidade: list[OpcaoSelect] = []
    opts_peso: list[OpcaoSelect] = []

    # Equipe: opções (todos os funcionários ativos) e quem está marcado.
    # Guardamos os ids como TEXTO para casar com o valor das checkboxes.
    funcionarios: list[OpcaoSelect] = []
    equipe_selecionada: list[str] = []

    @rx.var
    def todos_selecionados(self) -> bool:
        return (
            len(self.funcionarios) > 0
            and len(self.equipe_selecionada) == len(self.funcionarios)
        )

    def alternar_funcionario(self, fid: str):
        # Marca/desmarca um funcionário. Reatribuímos a lista (em vez de mutar no lugar)
        # para o Reflex perceber a mudança e redesenhar.
        if fid in self.equipe_selecionada:
            self.equipe_selecionada = [x for x in self.equipe_selecionada if x != fid]
        else:
            self.equipe_selecionada = self.equipe_selecionada + [fid]

    def alternar_todos(self):
        if self.todos_selecionados:
            self.equipe_selecionada = []
        else:
            self.equipe_selecionada = [f.valor for f in self.funcionarios]

    # ── READ: listagem ──
    def preparar_lista(self):
        """on_load da lista: carrega as opções do filtro de modalidade + a lista."""
        db = SessionLocal()
        try:
            self.opts_modalidade = [
                OpcaoSelect(valor=str(r.id), nome=r.nome)
                for r in crud_dominio.listar(db, Modalidade)
            ]
        finally:
            db.close()
        self.carregar_lista()

    def carregar_lista(self):
        # Traduz os sentinelas/textos dos filtros para o que o crud espera.
        status = None if self.filtro_status == "todos" else self.filtro_status
        modalidade_id = None if self.filtro_modalidade == "todas" else int(self.filtro_modalidade)
        data_de = date.fromisoformat(self.filtro_data_de) if self.filtro_data_de else None
        data_ate = date.fromisoformat(self.filtro_data_ate) if self.filtro_data_ate else None

        db = SessionLocal()
        try:
            self.ordens = [
                LinhaOS(
                    id=o.id,
                    numero=o.numero,
                    data_abertura=o.data_abertura.strftime("%d/%m/%Y"),
                    modalidade=o.modalidade.nome if o.modalidade else "—",
                    status=o.status,
                )
                for o in crud_os.listar(
                    db,
                    status=status,
                    modalidade_id=modalidade_id,
                    data_de=data_de,
                    data_ate=data_ate,
                )
            ]
        finally:
            db.close()

    # ── READ: detalhe de uma O.S. ──
    def carregar_detalhe(self):
        """Lê o id da URL (/ordens/[os_id]) e monta o DetalheOS."""
        os_id = self.router.page.params.get("os_id")
        try:
            oid = int(os_id)
        except (TypeError, ValueError):
            self.encontrada = False
            self.detalhe = DetalheOS()
            return  # sem id ou id não-numérico: mostra "não encontrada"
        self._carregar_por_id(oid)

    def _carregar_por_id(self, oid: int):
        """Monta o DetalheOS pelo id. Reusado também após mudar o status."""
        self.encontrada = False
        self.detalhe = DetalheOS()
        db = SessionLocal()
        try:
            o = crud_os.obter(db, oid)
            if o is None:
                return

            def nome(rel) -> str:
                # Atalho: pega .nome de uma FK que pode ser None.
                return rel.nome if rel else "—"

            self.detalhe = DetalheOS(
                id=o.id,
                numero=o.numero,
                status=o.status,
                data_abertura=o.data_abertura.strftime("%d/%m/%Y"),
                hora_abertura=o.hora_abertura.strftime("%H:%M"),
                operador=o.operador.nome if o.operador else "—",
                modalidade=nome(o.modalidade),
                classificacao=nome(o.classificacao),
                peso=nome(o.peso),
                meio=nome(o.meio),
                setor_demandante=nome(o.setor_demandante),
                unidade_atendimento=nome(o.unidade_atendimento),
                tipo_veiculo=nome(o.tipo_veiculo),
                requer_rota=o.requer_rota,
                processo_chamado=o.processo_chamado or "—",
                responsavel=o.responsavel or "—",
                contato=o.contato or "—",
                ambito=o.ambito or "—",
                endereco=o.endereco or "—",
                causa=o.causa or "—",
                descricao=o.descricao or "—",
                autorizado_por=o.autorizado_por or "—",
                data_conclusao=o.data_conclusao.strftime("%d/%m/%Y") if o.data_conclusao else "—",
                hora_inicial=o.hora_inicial.strftime("%H:%M") if o.hora_inicial else "—",
                hora_final=o.hora_final.strftime("%H:%M") if o.hora_final else "—",
                equipe=[v.funcionario.nome for v in o.equipe],
            )
            self.encontrada = True
        finally:
            db.close()

    # ── Carrega as opções dos dropdowns (só os ativos) ──
    def carregar_opcoes(self):
        self.error_message = ""
        db = SessionLocal()
        try:
            def opc(Model) -> list[OpcaoSelect]:
                return [
                    OpcaoSelect(valor=str(r.id), nome=r.nome)
                    for r in crud_dominio.listar(db, Model)
                ]

            self.opts_meio = opc(Meio)
            self.opts_setor = opc(Setor)
            self.opts_tipo_veiculo = opc(TipoVeiculo)
            self.opts_classificacao = opc(Classificacao)
            self.opts_modalidade = opc(Modalidade)
            self.opts_peso = opc(Peso)
            self.funcionarios = opc(Funcionario)
            self.equipe_selecionada = []  # começa o formulário com ninguém marcado
        finally:
            db.close()

    # ── CREATE ──
    async def criar(self, form_data: dict):
        self.error_message = ""

        # Os dois únicos campos obrigatórios (o resto a O.S. pode nascer sem).
        if not form_data.get("data_abertura") or not form_data.get("hora_abertura"):
            self.error_message = "Data e hora de abertura são obrigatórias."
            return

        # Helpers de conversão: FK vazia vira None; texto vazio vira None.
        def fk(campo: str):
            valor = form_data.get(campo)
            return int(valor) if valor else None

        def txt(campo: str):
            valor = (form_data.get(campo) or "").strip()
            return valor or None

        try:
            dados = {
                "data_abertura": date.fromisoformat(form_data["data_abertura"]),
                "hora_abertura": time.fromisoformat(form_data["hora_abertura"]),
                "processo_chamado": txt("processo_chamado"),
                "responsavel": txt("responsavel"),
                "contato": txt("contato"),
                "ambito": txt("ambito"),
                "endereco": txt("endereco"),
                "requer_rota": form_data.get("requer_rota") in ("on", "true", "1", True),
                "causa": txt("causa"),
                "descricao": txt("descricao"),
                "autorizado_por": txt("autorizado_por"),
                "meio_id": fk("meio_id"),
                "setor_demandante_id": fk("setor_demandante_id"),
                "unidade_atendimento_id": fk("unidade_atendimento_id"),
                "tipo_veiculo_id": fk("tipo_veiculo_id"),
                "classificacao_id": fk("classificacao_id"),
                "modalidade_id": fk("modalidade_id"),
                "peso_id": fk("peso_id"),
            }
        except ValueError:
            self.error_message = "Data ou hora em formato inválido."
            return

        # Pega o id do usuário logado de outro state (operador_id da O.S.).
        auth = await self.get_state(AuthState)

        # As checkboxes guardam ids como texto; o crud espera inteiros.
        equipe = [int(x) for x in self.equipe_selecionada]

        db = SessionLocal()
        try:
            crud_os.criar(db, int(auth.user_id), dados, equipe)
        finally:
            db.close()

        return rx.redirect("/ordens")  # volta para a lista, já com a nova O.S.

    # ── Mudança de status (na tela de detalhe) ──
    def ao_abrir_dialog(self, aberto: bool):
        """Chamado quando o diálogo de concluir abre/fecha. Ao abrir, sugere a data de hoje."""
        self.dialog_concluir = aberto
        self.error_message = ""
        if aberto:
            self.f_data_conclusao = date.today().isoformat()
            self.f_hora_inicial = ""
            self.f_hora_final = ""

    def concluir(self):
        self.error_message = ""
        if not self.f_data_conclusao:
            self.error_message = "Informe a data de conclusão."
            return
        try:
            data_conclusao = date.fromisoformat(self.f_data_conclusao)
            hora_inicial = time.fromisoformat(self.f_hora_inicial) if self.f_hora_inicial else None
            hora_final = time.fromisoformat(self.f_hora_final) if self.f_hora_final else None
        except ValueError:
            self.error_message = "Data ou hora em formato inválido."
            return

        db = SessionLocal()
        try:
            crud_os.concluir(db, self.detalhe.id, data_conclusao, hora_inicial, hora_final)
        finally:
            db.close()

        self.dialog_concluir = False
        self._carregar_por_id(self.detalhe.id)  # redesenha o detalhe já concluído

    def cancelar(self):
        db = SessionLocal()
        try:
            crud_os.cancelar(db, self.detalhe.id)
        finally:
            db.close()
        self._carregar_por_id(self.detalhe.id)

    def reabrir(self):
        db = SessionLocal()
        try:
            crud_os.reabrir(db, self.detalhe.id)
        finally:
            db.close()
        self._carregar_por_id(self.detalhe.id)
