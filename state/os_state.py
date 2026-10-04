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
    processo_chamado: str
    modalidade: str
    status: str


@dataclass
class ItemOS:
    """Um item (bem) de uma O.S., achatado para a tela — tudo texto.

    Campos vazios viram "" (nunca None), para a tela/impressão não ter que lidar com
    None: um campo em branco sai simplesmente em branco no papel.
    """

    tombo_ns: str = ""
    descricao: str = ""


@dataclass
class DetalheOS:
    """Todos os dados de uma O.S., já "achatados" para a tela de detalhe.

    Os nomes das FKs (modalidade, setor...) já vêm resolvidos como texto, a equipe
    como lista de nomes e os itens como lista de ItemOS. Todos os campos têm default,
    então DetalheOS() cria um vazio — útil como valor inicial (evita lidar com None).
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
    descricao: str = "—"
    autorizado_por: str = "—"
    data_conclusao: str = "—"
    hora_inicial: str = "—"
    hora_final: str = "—"
    equipe: list[str] = field(default_factory=list)
    itens: list[ItemOS] = field(default_factory=list)


# Campos "soltos" do formulário (name=...). São a base do dict de valores iniciais:
# vazios na criação, preenchidos na edição. NÃO inclui requer_rota (bool, tratado à
# parte) nem equipe/itens (controlados pelo state).
CAMPOS_FORM = (
    "data_abertura", "hora_abertura", "responsavel", "contato", "processo_chamado",
    "ambito", "autorizado_por", "endereco", "descricao",
    "modalidade_id", "classificacao_id", "peso_id", "meio_id",
    "setor_demandante_id", "unidade_atendimento_id", "tipo_veiculo_id",
)


def _form_vazio() -> dict[str, str]:
    """Valores iniciais em branco — o formulário de CRIAÇÃO nasce assim."""
    return {campo: "" for campo in CAMPOS_FORM}


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

    # Itens do formulário de criação. Cada linha é um dict com as 2 colunas; o operador
    # adiciona/remove linhas e digita nos campos. É controlado pelo state (não vai no
    # form_data) — mesma filosofia da equipe. Começa vazio: itens são OPCIONAIS.
    itens_form: list[dict[str, str]] = []

    # Edição: o MESMO formulário serve para criar e editar. editando_id = 0 significa
    # "criando"; > 0 significa "editando aquela O.S.". form_inicial alimenta o
    # default_value de cada campo solto (vazio na criação, preenchido na edição).
    editando_id: int = 0
    form_inicial: dict[str, str] = _form_vazio()
    form_requer_rota: bool = False

    @staticmethod
    def _item_vazio() -> dict[str, str]:
        return {"tombo_ns": "", "descricao": ""}

    def adicionar_item(self):
        # Reatribui a lista (em vez de mutar) para o Reflex perceber e redesenhar.
        self.itens_form = self.itens_form + [self._item_vazio()]

    def remover_item(self, idx: int):
        self.itens_form = [it for i, it in enumerate(self.itens_form) if i != idx]

    def set_item_campo(self, idx: int, campo: str, valor: str):
        """Atualiza um campo de uma linha. Copiamos os dicts para o Reflex ver a mudança."""
        novos = [dict(it) for it in self.itens_form]
        novos[idx][campo] = valor
        self.itens_form = novos

    @rx.var
    def itens_impressao_vazias(self) -> list[int]:
        """Quantas linhas EM BRANCO faltam para a tabela de itens da impressão chegar a 10.

        A impressão mostra os itens digitados + linhas em branco até completar 10, para
        o funcionário poder anotar bens a mais à mão. Devolve os índices dessas linhas.
        """
        faltam = 10 - len(self.detalhe.itens)
        return list(range(max(faltam, 0)))

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
                    processo_chamado=o.processo_chamado or "—",
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
                descricao=o.descricao or "—",
                autorizado_por=o.autorizado_por or "—",
                data_conclusao=o.data_conclusao.strftime("%d/%m/%Y") if o.data_conclusao else "—",
                hora_inicial=o.hora_inicial.strftime("%H:%M") if o.hora_inicial else "—",
                hora_final=o.hora_final.strftime("%H:%M") if o.hora_final else "—",
                equipe=[v.funcionario.nome for v in o.equipe],
                itens=[
                    ItemOS(
                        tombo_ns=i.tombo_ns or "",
                        descricao=i.descricao or "",
                    )
                    for i in o.itens
                ],
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
            self.itens_form = []  # começa sem nenhum item (a seção é opcional)
            # Modo criação: sem O.S. em edição e todos os campos em branco.
            self.editando_id = 0
            self.form_inicial = _form_vazio()
            self.form_requer_rota = False
        finally:
            db.close()

    # ── Carrega o formulário JÁ PREENCHIDO para editar uma O.S. existente ──
    def carregar_edicao(self):
        """on_load da rota /ordens/[os_id]/editar: dropdowns + valores da O.S. no form."""
        self.carregar_opcoes()  # carrega os dropdowns e zera tudo (modo criação)

        os_id = self.router.page.params.get("os_id")
        try:
            oid = int(os_id)
        except (TypeError, ValueError):
            self.editando_id = 0
            return  # sem id válido: fica em modo criação (form vazio)

        db = SessionLocal()
        try:
            o = crud_os.obter(db, oid)
            if o is None:
                self.editando_id = 0
                return

            def fk_txt(valor) -> str:
                # id da FK como texto (casa com o value das opções do select); "" se None.
                return str(valor) if valor else ""

            self.editando_id = o.id
            self.form_inicial = {
                "data_abertura": o.data_abertura.isoformat() if o.data_abertura else "",
                "hora_abertura": o.hora_abertura.strftime("%H:%M") if o.hora_abertura else "",
                "responsavel": o.responsavel or "",
                "contato": o.contato or "",
                "processo_chamado": o.processo_chamado or "",
                "ambito": o.ambito or "",
                "autorizado_por": o.autorizado_por or "",
                "endereco": o.endereco or "",
                "descricao": o.descricao or "",
                "modalidade_id": fk_txt(o.modalidade_id),
                "classificacao_id": fk_txt(o.classificacao_id),
                "peso_id": fk_txt(o.peso_id),
                "meio_id": fk_txt(o.meio_id),
                "setor_demandante_id": fk_txt(o.setor_demandante_id),
                "unidade_atendimento_id": fk_txt(o.unidade_atendimento_id),
                "tipo_veiculo_id": fk_txt(o.tipo_veiculo_id),
            }
            self.form_requer_rota = o.requer_rota
            # Equipe e itens já são controlados pelo state: basta pré-carregar.
            self.equipe_selecionada = [str(v.funcionario_id) for v in o.equipe]
            self.itens_form = [
                {
                    "tombo_ns": i.tombo_ns or "",
                    "descricao": i.descricao or "",
                }
                for i in o.itens
            ]
        finally:
            db.close()

    # ── CREATE / UPDATE (o mesmo formulário serve para os dois) ──
    async def salvar(self, form_data: dict):
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

        # As checkboxes guardam ids como texto; o crud espera inteiros.
        equipe = [int(x) for x in self.equipe_selecionada]

        # Monta os itens a gravar: descarta linhas TOTALMENTE em branco (o operador pode
        # ter adicionado uma linha e não preenchido). Nas que sobram, cada campo vazio
        # vira None. Campos individuais podem ficar vazios (ex.: um bem sem tombo).
        itens = []
        for linha in self.itens_form:
            campos = {c: (linha.get(c) or "").strip() or None for c in
                      ("tombo_ns", "descricao")}
            if any(campos.values()):
                itens.append(campos)

        db = SessionLocal()
        try:
            if self.editando_id:
                # EDIÇÃO: sobrescreve os dados da O.S. existente; número/operador intactos.
                crud_os.atualizar(db, self.editando_id, dados, equipe, itens)
                destino = f"/ordens/{self.editando_id}"  # volta pro detalhe corrigido
            else:
                # CRIAÇÃO: operador vem do usuário logado (outro state).
                auth = await self.get_state(AuthState)
                crud_os.criar(db, int(auth.user_id), dados, equipe, itens)
                destino = "/ordens"  # volta pra lista, já com a nova O.S.
        finally:
            db.close()

        return rx.redirect(destino)

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
