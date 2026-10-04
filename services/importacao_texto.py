"""Leitura de uma lista de O.S. colada como texto (ex.: copiada do WhatsApp).

É Python puro — sem Reflex e sem banco — de propósito, como o services/exportacao.py:
dá para testar sem subir o app. Este módulo só ENTENDE o texto. Quem grava no banco, e
quem confere se o setor/modalidade existem, é a camada de cima (a tela).

FORMATO (uma linha por registro, campos separados por ';' ou por TAB — cola do Excel):

    Chamado;Setor;Modalidade;Descrição;Responsável        <- uma O.S. (5 campos)
    item;Tombo ou N/S;Descrição                           <- um item (3 campos)

- "item" é só a MARCA da linha; não é gravada. O item pertence à última O.S. acima.
- A contagem de campos é EXATA. Campo vazio fica só com o ';'. Linha com número errado
  de campos é recusada, nunca gravada com dados trocados.
- Obrigatórios na O.S.: Chamado, Setor, Modalidade e Descrição. Responsável é opcional.
- Item é todo opcional, mas uma linha 'item;;' totalmente vazia é descartada.
"""

import re
from dataclasses import dataclass, field

CAMPOS_OS = 5
CAMPOS_ITEM = 3
MARCA_ITEM = "item"

# Cabeçalho que o WhatsApp cola antes da mensagem, nos dois formatos mais comuns:
#   [12/03/2026 14:30] Maria: ...      (iPhone)
#   12/03/2026 14:30 - Maria: ...      (Android)
_CABECALHO_WHATSAPP = re.compile(
    r"^\s*(?:"
    r"\[\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\]"
    r"|"
    r"\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s+-"
    r")\s*[^:;\t]+:\s*"
)


@dataclass
class ItemLido:
    tombo_ns: str | None
    descricao: str | None
    linha: int = 0  # número da linha no texto colado


@dataclass
class OsLida:
    linha: int  # número da linha no texto colado (1 = primeira), para mostrar ao usuário
    chamado: str
    setor: str
    modalidade: str
    descricao: str
    responsavel: str | None
    itens: list[ItemLido] = field(default_factory=list)


@dataclass
class Sugestao:
    """Um valor do cadastro parecido com o que foi digitado, para corrigir com um clique."""

    campo: str  # "Setor" ou "Modalidade" (rótulo mostrado na tela)
    indice: int  # posição do campo na linha da O.S. (0 = Chamado, 1 = Setor, ...)
    valor: str  # o nome exato do cadastro


@dataclass
class ErroLinha:
    linha: int
    mensagem: str
    texto: str  # a linha original, para o usuário reconhecer o que errou
    sugestoes: list[Sugestao] = field(default_factory=list)


@dataclass
class Resultado:
    ordens: list[OsLida] = field(default_factory=list)
    erros: list[ErroLinha] = field(default_factory=list)
    avisos: list[ErroLinha] = field(default_factory=list)  # não impedem gravar


def _vazio_para_none(texto: str) -> str | None:
    texto = texto.strip()
    return texto or None


def _separar(linha: str) -> list[str]:
    """TAB se houver (cola do Excel), senão ponto-e-vírgula. Campos já sem espaços."""
    separador = "\t" if "\t" in linha else ";"
    return [campo.strip() for campo in linha.split(separador)]


def substituir_campo(texto: str, linha: int, indice: int, novo: str) -> str:
    """Troca UM campo de UMA linha do texto colado, sem mexer no resto.

    `linha` é o número mostrado ao usuário (1 = primeira); `indice` é a posição do campo
    (0 = Chamado, 1 = Setor, 2 = Modalidade...). Preserva o cabeçalho do WhatsApp e o
    separador original (';' ou TAB). Se linha ou campo não existirem, devolve o texto
    como estava.
    """
    linhas = texto.splitlines()
    if not 1 <= linha <= len(linhas):
        return texto

    original = linhas[linha - 1]
    cabecalho = _CABECALHO_WHATSAPP.match(original)
    prefixo = cabecalho.group(0) if cabecalho else ""
    corpo = original[len(prefixo):]

    separador = "\t" if "\t" in corpo else ";"
    campos = corpo.split(separador)
    if not 0 <= indice < len(campos):
        return texto

    campos[indice] = novo
    linhas[linha - 1] = prefixo + separador.join(campos)
    return "\n".join(linhas)


def interpretar(texto: str) -> Resultado:
    resultado = Resultado()
    os_atual: OsLida | None = None  # última O.S. VÁLIDA acima
    os_atual_recusada = False  # a última linha de O.S. foi recusada?
    chamados_vistos: dict[str, int] = {}

    for numero, original in enumerate(texto.splitlines(), start=1):
        linha = _CABECALHO_WHATSAPP.sub("", original).strip()
        if not linha:
            continue

        campos = _separar(linha)

        if campos[0].casefold() == MARCA_ITEM:
            _ler_item(resultado, numero, original, campos, os_atual, os_atual_recusada)
            continue

        os_lida = _ler_os(resultado, numero, original, campos)
        os_atual_recusada = os_lida is None
        os_atual = os_lida
        if os_lida is None:
            continue

        anterior = chamados_vistos.get(os_lida.chamado)
        if anterior is not None:
            resultado.avisos.append(
                ErroLinha(
                    numero,
                    f"Chamado '{os_lida.chamado}' repetido (já aparece na linha {anterior}).",
                    original,
                )
            )
        else:
            chamados_vistos[os_lida.chamado] = numero
        resultado.ordens.append(os_lida)

    return resultado


def _ler_os(
    resultado: Resultado, numero: int, original: str, campos: list[str]
) -> OsLida | None:
    if len(campos) != CAMPOS_OS:
        resultado.erros.append(
            ErroLinha(
                numero,
                f"A O.S. precisa de {CAMPOS_OS} campos e a linha tem {len(campos)}.",
                original,
            )
        )
        return None

    chamado, setor, modalidade, descricao, responsavel = campos
    faltando = [
        nome
        for nome, valor in (
            ("Chamado", chamado),
            ("Setor", setor),
            ("Modalidade", modalidade),
            ("Descrição", descricao),
        )
        if not valor
    ]
    if faltando:
        resultado.erros.append(
            ErroLinha(numero, f"Campo obrigatório vazio: {', '.join(faltando)}.", original)
        )
        return None

    return OsLida(
        linha=numero,
        chamado=chamado,
        setor=setor,
        modalidade=modalidade,
        descricao=descricao,
        responsavel=_vazio_para_none(responsavel),
    )


def _ler_item(
    resultado: Resultado,
    numero: int,
    original: str,
    campos: list[str],
    os_atual: OsLida | None,
    os_atual_recusada: bool,
) -> None:
    if len(campos) != CAMPOS_ITEM:
        resultado.erros.append(
            ErroLinha(
                numero,
                f"O item precisa de {CAMPOS_ITEM} campos ('item', tombo e descrição) "
                f"e a linha tem {len(campos)}.",
                original,
            )
        )
        return

    if os_atual is None:
        motivo = (
            "A O.S. acima foi recusada, então o item também foi."
            if os_atual_recusada
            else "Item sem O.S. acima."
        )
        resultado.erros.append(ErroLinha(numero, motivo, original))
        return

    tombo = _vazio_para_none(campos[1])
    descricao = _vazio_para_none(campos[2])
    if tombo is None and descricao is None:
        return  # linha 'item;;' vazia: descartada, como o formulário faz
    os_atual.itens.append(ItemLido(tombo, descricao, numero))
