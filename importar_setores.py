"""Importa a lista de setores/unidades de um arquivo CSV para a tabela `setor`.

Lembre: existe UMA tabela `setor` só, e ela alimenta os DOIS campos da O.S.
("Setor demandante" e "Unidade de atendimento"). Então basta importar aqui uma vez.

É IDEMPOTENTE: pode rodar quantas vezes quiser. Antes de inserir, confere o que já
existe na tabela e só adiciona o que falta — nunca duplica.

COMO USAR:
1. Coloque seu CSV na pasta do projeto (ou anote o caminho completo dele).
2. Ajuste as 4 constantes de configuração logo abaixo (principalmente CSV_PATH e
   COLUNA_NOME).
3. Rode, com o venv ativado:
       python importar_setores.py
"""

import csv

from services.database import SessionLocal
from models.dominio import Setor

# ─────────────────────────── CONFIGURAÇÃO ───────────────────────────
# Caminho do arquivo CSV. Pode ser só o nome (se estiver na pasta do projeto)
# ou o caminho completo (ex.: r"C:\Users\migue\Downloads\setores.csv").
CSV_PATH = "unidades_rows.csv"

# Nome da COLUNA do CSV que contém o nome do setor/unidade.
# Se o seu CSV NÃO tiver cabeçalho (é só uma lista de nomes numa coluna), deixe
# COLUNA_NOME = None e ajuste TEM_CABECALHO = False.
COLUNA_NOME = None

# O CSV tem uma primeira linha de cabeçalho (nomes das colunas)? True/False.
TEM_CABECALHO = False

# Separador de colunas. Excel em português costuma salvar com ";" (ponto e vírgula).
# Se seu arquivo usa vírgula, troque para ",".
DELIMITADOR = ","

# Codificação do arquivo. "utf-8-sig" cobre a maioria dos CSVs do Excel (com BOM).
# Se aparecerem acentos estranhos (Ã, Â...), tente "latin-1".
ENCODING = "utf-8-sig"
# ─────────────────────────────────────────────────────────────────────


def ler_nomes() -> list[str]:
    """Lê o CSV e devolve a lista de nomes, já sem vazios e sem repetidos no arquivo."""
    nomes: list[str] = []
    with open(CSV_PATH, newline="", encoding=ENCODING) as f:
        if TEM_CABECALHO:
            leitor = csv.DictReader(f, delimiter=DELIMITADOR)
            for linha in leitor:
                nomes.append((linha.get(COLUNA_NOME) or "").strip())
        else:
            leitor = csv.reader(f, delimiter=DELIMITADOR)
            for linha in leitor:
                if linha:  # ignora linhas em branco
                    nomes.append((linha[0] or "").strip())

    # Remove vazios e duplicados DENTRO do arquivo, preservando a ordem.
    vistos: set[str] = set()
    unicos: list[str] = []
    for nome in nomes:
        if nome and nome not in vistos:
            vistos.add(nome)
            unicos.append(nome)
    return unicos


def main() -> None:
    nomes = ler_nomes()
    print(f">> {len(nomes)} nome(s) lido(s) do arquivo '{CSV_PATH}'.")

    db = SessionLocal()
    try:
        # Nomes que já existem na tabela (ativos ou não) — para não duplicar.
        existentes = {nome for (nome,) in db.query(Setor.nome).all()}

        inseridos = 0
        for nome in nomes:
            if nome in existentes:
                continue  # já está no banco — pula
            db.add(Setor(nome=nome))
            existentes.add(nome)
            inseridos += 1
            print(f"   + setor: {nome}")

        db.commit()  # só agora grava de fato
        print(f"\n>> Concluído: {inseridos} novo(s) inserido(s), "
              f"{len(nomes) - inseridos} já existia(m).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
