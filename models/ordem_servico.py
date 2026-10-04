"""Ordem de Serviço — a entidade central do sistema.

Reúne os dados da abertura, o ciclo de vida (status/datas) e as ligações (FKs) para as
tabelas de domínio, o operador (User) e a equipe (Funcionario, via junção os_equipe).
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.database import Base
from models.mixins import TimestampMixin

if TYPE_CHECKING:  # só para o editor entender os tipos; não roda em tempo de execução
    from models.user import User
    from models.dominio import (
        Meio,
        Classificacao,
        Peso,
        TipoVeiculo,
        Modalidade,
        Setor,
    )
    from models.funcionario import Funcionario


class OrdemServico(Base, TimestampMixin):
    __tablename__ = "ordem_servico"

    id: Mapped[int] = mapped_column(primary_key=True)  # PK técnica interna
    # Código de negócio que o humano lê (ex.: H1110). Gerado automaticamente no crud;
    # o operador NUNCA digita. unique garante que não se repita.
    numero: Mapped[str] = mapped_column(unique=True, index=True)

    # --- dados da abertura ---
    data_abertura: Mapped[date]
    hora_abertura: Mapped[time]
    processo_chamado: Mapped[str | None]
    responsavel: Mapped[str | None]
    contato: Mapped[str | None]
    ambito: Mapped[str | None]
    endereco: Mapped[str | None]
    requer_rota: Mapped[bool] = mapped_column(default=False)
    descricao: Mapped[str | None]
    autorizado_por: Mapped[str | None]

    # --- ciclo de vida ---
    status: Mapped[str] = mapped_column(default="Pendente")  # Pendente|Concluída|Cancelada
    data_conclusao: Mapped[date | None]
    hora_inicial: Mapped[time | None]
    hora_final: Mapped[time | None]

    # --- chaves estrangeiras (cada O.S. aponta para 1 registro de cada lista) ---
    operador_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    meio_id: Mapped[int | None] = mapped_column(ForeignKey("meio.id"))
    setor_demandante_id: Mapped[int | None] = mapped_column(ForeignKey("setor.id"))
    unidade_atendimento_id: Mapped[int | None] = mapped_column(ForeignKey("setor.id"))
    tipo_veiculo_id: Mapped[int | None] = mapped_column(ForeignKey("tipo_veiculo.id"))
    classificacao_id: Mapped[int | None] = mapped_column(ForeignKey("classificacao.id"))
    modalidade_id: Mapped[int | None] = mapped_column(ForeignKey("modalidade.id"))
    peso_id: Mapped[int | None] = mapped_column(ForeignKey("peso.id"))

    # --- relacionamentos (atalhos em Python: os.modalidade.nome, etc.) ---
    operador: Mapped["User"] = relationship()
    meio: Mapped["Meio | None"] = relationship()
    tipo_veiculo: Mapped["TipoVeiculo | None"] = relationship()
    classificacao: Mapped["Classificacao | None"] = relationship()
    modalidade: Mapped["Modalidade | None"] = relationship()
    peso: Mapped["Peso | None"] = relationship()
    # Setor aparece duas vezes apontando para a MESMA tabela; por isso precisamos dizer
    # explicitamente qual coluna (foreign_keys) alimenta cada atalho.
    setor_demandante: Mapped["Setor | None"] = relationship(
        foreign_keys=[setor_demandante_id]
    )
    unidade_atendimento: Mapped["Setor | None"] = relationship(
        foreign_keys=[unidade_atendimento_id]
    )

    # equipe: lista de vínculos com funcionários (N:N via os_equipe)
    equipe: Mapped[list["OsEquipe"]] = relationship(
        back_populates="ordem", cascade="all, delete-orphan"
    )

    # itens: bens movimentados/atendidos nesta O.S. (1:N via os_item). Mesmo padrão da
    # equipe. order_by garante que saiam na impressão na ordem em que foram cadastrados.
    itens: Mapped[list["OsItem"]] = relationship(
        back_populates="ordem",
        cascade="all, delete-orphan",
        order_by="OsItem.id",
    )


class OsEquipe(Base):
    """Tabela de junção: liga uma O.S. a cada funcionário que atuou nela.

    A planilha original tinha 12 colunas de nomes; aqui vira uma linha por funcionário.
    """

    __tablename__ = "os_equipe"

    id: Mapped[int] = mapped_column(primary_key=True)
    os_id: Mapped[int] = mapped_column(ForeignKey("ordem_servico.id"))
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionario.id"))

    ordem: Mapped["OrdemServico"] = relationship(back_populates="equipe")
    funcionario: Mapped["Funcionario"] = relationship()


class OsItem(Base):
    """Um bem movimentado/atendido numa O.S.: tombo (ou nº de série) e descrição.

    Antes isto só existia como uma tabela EM BRANCO no papel (preenchida à mão). Agora
    virou dado: cada O.S. tem zero-ou-mais itens (1:N), cadastrados já na criação. É o
    mesmo desenho da equipe (OsEquipe) — uma linha por item, ligada à O.S. pelo os_id.

    Os dois campos são opcionais: o operador pode deixar um em branco (ex.: um bem sem
    tombo). A ausência de itens também é permitida (a seção é opcional na criação).
    """

    __tablename__ = "os_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    os_id: Mapped[int] = mapped_column(ForeignKey("ordem_servico.id"))
    tombo_ns: Mapped[str | None]  # "Tombo ou N/S" no formulário/impressão
    descricao: Mapped[str | None]

    ordem: Mapped["OrdemServico"] = relationship(back_populates="itens")
