"""Segunda etapa da importação em lote: ligar o texto lido ao que existe no cadastro.

O parser (importacao_texto.py) só entende o TEXTO. Aqui conferimos o que ele não sabe:
o setor e a modalidade digitados existem? O Chamado já está no banco?

Continua sendo Python puro — quem consulta o banco é a tela, que entrega aqui os
dicionários prontos. Assim dá para testar sem PostgreSQL.
"""

import difflib
import re
import unicodedata
from dataclasses import dataclass, field

from services.importacao_texto import ErroLinha, ItemLido, OsLida, Resultado, Sugestao

# Posição de cada campo na linha da O.S. (usada para corrigir com um clique).
INDICE_SETOR = 1
INDICE_MODALIDADE = 2
MAX_SUGESTOES = 5
_ORDINAL_SEM_SIMBOLO = re.compile(r"(?<=\d)[ao](?=\s|$)")
_CORTE_PARECIDO = 0.7  # semelhança mínima de grafia para sugerir
_MARGEM_PARECIDO = 0.03 # só sugere os que ficam perto do melhor

# Valores que toda O.S. importada recebe, já que a linha colada não traz esses campos.
# São NOMES de cadastro; se o admin renomear um deles, o campo fica vazio (sem erro).
MEIO_PADRAO = "Chamado"
CLASSIFICACAO_PADRAO = "Normal"
PESO_PADRAO = "Normal"


def normalizar(nome: str) -> str:
    """Chave de comparação: sem acento, minúscula, espaços repetidos viram um só.

    Quem digita no WhatsApp escreve "Manutencao" ou "manutenção"; as duas devem achar
    "Manutenção" no cadastro. Os indicadores ordinais ª, º e ° (o cadastro usa "21° Vara")
    também são ignorados: "3ª", "3º" e "3°" são a mesma coisa para quem digita.
    """
    nome = nome.translate({ord("ª"): None, ord("º"): None, ord("°"): None})
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", nome) if not unicodedata.combining(c)
    )
    # "3a Vara" / "3o Vara": quem não acha o símbolo no teclado digita a letra no lugar.
    # Só vale colada a um número e no fim da palavra, para não mexer em nomes comuns.
    sem_ordinal = _ORDINAL_SEM_SIMBOLO.sub("", sem_acento.casefold())
    return " ".join(sem_ordinal.split())


def indexar(nomes_ids: list[tuple[str, int]]) -> dict[str, int]:
    """[(nome, id), ...] -> {nome normalizado: id}, para usar em `resolver`."""
    indice: dict[str, int] = {}
    for nome, id_ in nomes_ids:
        indice.setdefault(normalizar(nome), id_)
    return indice


def nomes_por_chave(nomes: list[str]) -> dict[str, str]:
    """{nome normalizado: nome original}, para devolver o nome EXATO do cadastro."""
    return {normalizar(n): n for n in nomes}


def sugerir(valor: str, nomes: dict[str, str]) -> list[str]:
    """Nomes do cadastro parecidos com o que foi digitado (até MAX_SUGESTOES).

    Duas fontes, usadas nesta ordem (a segunda só se a primeira não achar nada):
    1. Nomes que CONTÊM todas as palavras digitadas: "vara milagres" acha
       "Vara Única da Comarca de Milagres". Os mais curtos primeiro (mais específicos).
    2. Nomes de grafia parecida (difflib, da biblioteca padrão): pega erro de digitação,
       como "Recolhimeto". Fica só com os que chegam perto do melhor, para a lista não
       virar ruído (senão "3a Vara" traria também a 39ª, 38ª, 37ª...).
    """
    chave = normalizar(valor)
    palavras = set(chave.split())
    contem = sorted(
        (k for k in nomes if palavras and palavras <= set(k.split())), key=len
    )
    if contem:
        return [nomes[k] for k in contem[:MAX_SUGESTOES]]

    parecidas = difflib.get_close_matches(
        chave, list(nomes), n=MAX_SUGESTOES, cutoff=_CORTE_PARECIDO
    )
    if not parecidas:
        return []
    notas = {k: difflib.SequenceMatcher(None, chave, k).ratio() for k in parecidas}
    melhor = max(notas.values())
    return [nomes[k] for k in parecidas if notas[k] >= melhor - _MARGEM_PARECIDO]


@dataclass
class OsPronta:
    """Uma O.S. que passou em todas as conferências e pode ser gravada."""

    linha: int
    chamado: str
    setor: str
    modalidade: str
    descricao: str
    responsavel: str | None
    setor_id: int
    modalidade_id: int
    itens: list[ItemLido] = field(default_factory=list)


@dataclass
class Previa:
    prontas: list[OsPronta] = field(default_factory=list)
    erros: list[ErroLinha] = field(default_factory=list)
    avisos: list[ErroLinha] = field(default_factory=list)

    def texto_dos_erros(self) -> str:
        """As linhas recusadas, na ordem original — para o usuário corrigir e tentar de novo."""
        return "\n".join(e.texto for e in sorted(self.erros, key=lambda e: e.linha))


def resolver(
    lido: Resultado,
    setores: dict[str, int],
    modalidades: dict[str, int],
    chamados_existentes: set[str],
    nomes_setores: dict[str, str] | None = None,
    nomes_modalidades: dict[str, str] | None = None,
) -> Previa:
    """Confere cada O.S. lida contra o cadastro.

    - Setor/modalidade desconhecidos: a O.S. é RECUSADA (erro) — nunca inventamos cadastro.
      Os itens dela também ficam de fora, e o erro de cada um explica por quê.
      Se `nomes_setores`/`nomes_modalidades` vierem (ver `nomes_por_chave`), o erro leva
      SUGESTÕES de nomes parecidos para o operador corrigir com um clique.
    - Chamado que já existe no banco: só AVISO — pode ser legítimo ter mais de uma O.S.
      para o mesmo chamado, então quem decide é o operador.
    """
    previa = Previa(erros=list(lido.erros), avisos=list(lido.avisos))

    for os_ in lido.ordens:
        problemas = []
        sugestoes: list[Sugestao] = []
        setor_id = setores.get(normalizar(os_.setor))
        if setor_id is None:
            problemas.append(f"Setor '{os_.setor}' não está cadastrado.")
            if nomes_setores:
                sugestoes += [
                    Sugestao("Setor", INDICE_SETOR, nome)
                    for nome in sugerir(os_.setor, nomes_setores)
                ]
        modalidade_id = modalidades.get(normalizar(os_.modalidade))
        if modalidade_id is None:
            problemas.append(f"Modalidade '{os_.modalidade}' não está cadastrada.")
            if nomes_modalidades:
                sugestoes += [
                    Sugestao("Modalidade", INDICE_MODALIDADE, nome)
                    for nome in sugerir(os_.modalidade, nomes_modalidades)
                ]

        if problemas:
            previa.erros.append(
                ErroLinha(os_.linha, " ".join(problemas), _reconstituir(os_), sugestoes)
            )
            # Os itens dessa O.S. não têm onde ser gravados: viram erro também, para
            # voltarem à caixa de texto junto com a linha da O.S.
            for item in os_.itens:
                previa.erros.append(
                    ErroLinha(
                        item.linha,
                        "A O.S. acima foi recusada, então o item também foi.",
                        _reconstituir_item(item),
                    )
                )
            continue

        if os_.chamado in chamados_existentes:
            previa.avisos.append(
                ErroLinha(
                    os_.linha,
                    f"Chamado '{os_.chamado}' já existe no sistema. "
                    "Será criada outra O.S. para ele.",
                    _reconstituir(os_),
                )
            )

        previa.prontas.append(
            OsPronta(
                linha=os_.linha,
                chamado=os_.chamado,
                setor=os_.setor,
                modalidade=os_.modalidade,
                descricao=os_.descricao,
                responsavel=os_.responsavel,
                setor_id=setor_id,
                modalidade_id=modalidade_id,
                itens=os_.itens,
            )
        )

    return previa


def _reconstituir(os_: OsLida) -> str:
    """A linha da O.S. de volta em texto (o original não é guardado pelo parser)."""
    return ";".join(
        [os_.chamado, os_.setor, os_.modalidade, os_.descricao, os_.responsavel or ""]
    )


def _reconstituir_item(item: ItemLido) -> str:
    return f"item;{item.tombo_ns or ''};{item.descricao or ''}"
