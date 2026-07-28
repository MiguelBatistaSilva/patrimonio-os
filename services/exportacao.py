"""Geração do arquivo CSV das Ordens de Serviço.

Recebe as O.S. já lidas do banco (pelo crud) e devolve os BYTES do arquivo pronto.
É Python puro — sem Reflex e sem banco — de propósito: assim dá para testar o
formato do arquivo sem subir o app nem tocar no PostgreSQL.

DOIS DETALHES QUE DECIDEM SE O EXCEL ABRE O ARQUIVO DIREITO (em português):
1. Separador PONTO-E-VÍRGULA. O Excel-PT espera ';'. Com vírgula, ele despeja a
   linha inteira numa coluna só e o usuário acha que "o arquivo veio quebrado".
2. UTF-8 COM BOM ("utf-8-sig"). O BOM é uma marca invisível no começo do arquivo que
   avisa o Excel que o texto é UTF-8. Sem ela, "Patrimônio" vira "PatrimÃ´nio".
"""

import csv
import io
from datetime import date

# A ordem aqui é a ordem das colunas na planilha. Mudou aqui, mudou em _linha().
CABECALHO = [
    "Número",
    "Status",
    "Data de abertura",
    "Hora de abertura",
    "Data de conclusão",
    "Hora inicial",
    "Hora final",
    "Modalidade",
    "Classificação",
    "Peso",
    "Meio",
    "Setor demandante",
    "Unidade de atendimento",
    "Tipo de veículo",
    "Requer rota",
    "Processo / Chamado",
    "Responsável",
    "Contato",
    "Âmbito",
    "Endereço",
    "Descrição",
    "Autorizado por",
    "Operador",
    "Equipe",
    "Qtd. de itens",
]


def _data(valor) -> str:
    """Data no formato brasileiro. Vazio vira "" (célula em branco na planilha)."""
    return valor.strftime("%d/%m/%Y") if valor else ""


def _hora(valor) -> str:
    return valor.strftime("%H:%M") if valor else ""


def _nome(rel) -> str:
    """Nome de uma tabela ligada (modalidade, setor...) que pode ser nula."""
    return rel.nome if rel else ""


def _texto(valor) -> str:
    """Texto livre achatado numa linha só.

    Descrição e Endereço vêm de campos de texto grandes, onde o operador pode ter dado
    Enter. Uma quebra de linha DENTRO de uma célula é CSV válido (o csv.writer põe
    aspas), mas deixa a planilha com linhas altíssimas e costuma confundir outros
    programas que leiam o arquivo depois. Trocamos por espaço.
    """
    if not valor:
        return ""
    return " ".join(str(valor).split())


def _linha(o) -> list[str]:
    """Uma O.S. vira uma linha da planilha. Mesma ordem do CABECALHO."""
    return [
        o.numero,
        o.status,
        _data(o.data_abertura),
        _hora(o.hora_abertura),
        _data(o.data_conclusao),
        _hora(o.hora_inicial),
        _hora(o.hora_final),
        _nome(o.modalidade),
        _nome(o.classificacao),
        _nome(o.peso),
        _nome(o.meio),
        _nome(o.setor_demandante),
        _nome(o.unidade_atendimento),
        _nome(o.tipo_veiculo),
        "Sim" if o.requer_rota else "Não",
        _texto(o.processo_chamado),
        _texto(o.responsavel),
        _texto(o.contato),
        _texto(o.ambito),
        _texto(o.endereco),
        _texto(o.descricao),
        _texto(o.autorizado_por),
        o.operador.nome if o.operador else "",
        # A equipe é uma lista; vira uma célula só com os nomes separados por vírgula.
        ", ".join(v.funcionario.nome for v in o.equipe if v.funcionario),
        str(len(o.itens)),
    ]


def gerar_csv(ordens) -> bytes:
    """Monta o arquivo inteiro na memória e devolve os bytes prontos para download."""
    buffer = io.StringIO(newline="")
    escritor = csv.writer(
        buffer,
        delimiter=";",          # o que o Excel-PT espera
        quoting=csv.QUOTE_MINIMAL,  # só põe aspas quando precisa (';' ou aspas no texto)
        lineterminator="\r\n",  # fim de linha do Windows
    )
    escritor.writerow(CABECALHO)
    escritor.writerows(_linha(o) for o in ordens)
    return buffer.getvalue().encode("utf-8-sig")  # "sig" = com BOM (ver docstring)


def nome_arquivo(data_de=None, data_ate=None) -> str:
    """Nome sugerido do arquivo — já diz de cara o que tem dentro.

    Datas no formato ANO-MÊS-DIA para os arquivos ficarem em ordem cronológica quando
    o chefe olhar a pasta de Downloads ordenada por nome.

    Exportar duas vezes seguidas gera o mesmo nome — e tudo bem: o próprio navegador
    resolve acrescentando "(1)", como faz com qualquer download repetido.
    """
    if data_de and data_ate:
        return f"ordens_servico_{data_de:%Y-%m-%d}_a_{data_ate:%Y-%m-%d}.csv"
    if data_de:
        return f"ordens_servico_a_partir_de_{data_de:%Y-%m-%d}.csv"
    if data_ate:
        return f"ordens_servico_ate_{data_ate:%Y-%m-%d}.csv"
    return f"ordens_servico_completo_{date.today():%Y-%m-%d}.csv"
