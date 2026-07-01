"""Popula o banco com os dados iniciais (seed = "semente").

Faz duas coisas:
1. Preenche as tabelas de domínio com os valores reais da Seção.
2. Cria o primeiro usuário admin (você), para conseguir logar no sistema.

É IDEMPOTENTE: pode rodar quantas vezes quiser. Antes de inserir, ele confere o que já
existe e só adiciona o que falta — nunca duplica.

    ./.venv/Scripts/python.exe seed.py
"""

from services.database import SessionLocal
from services.security import hash_password
from models.user import User
from models.dominio import (
    Meio,
    Classificacao,
    Peso,
    TipoVeiculo,
    Modalidade,
    Setor,
)

# --- Primeiro usuário admin (edite estas 3 linhas) ---
# É com estes dados que você vai logar no sistema. Troque a senha por uma sua.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "tjce@123"
ADMIN_NOME = "Administrador"

# Mapa: para cada tabela de domínio, a lista de valores iniciais.
# Ajuste estas listas à vontade — é exatamente o que o admin poderá fazer pela tela depois.
DOMINIOS = {
    Meio: ["Chamado"],
    Classificacao: ["Normal", "Urgente"],
    Peso: ["1", "2", "3", "5", "Normal"],  # escala a confirmar com o cliente
    TipoVeiculo: ["Grande", "Médio", "Pequeno"],
    Modalidade: [
        "Abertura de Rack", "Acerto de Localização", "Assinatura", "Concessão",
        "Conferência", "Configuração", "Controle", "Devolução", "Empréstimo",
        "Entrega", "Envio", "Garantia", "Inventário", "Lavagem", "Limpeza",
        "Localização", "Movimentação", "Permuta", "Recolhimento", "Remanejamento",
        "Reparo", "Substituição",
    ],
    Setor: [],  # vazio: os setores reais entram depois pelo CRUD do admin
}


def seed_dominios(db) -> None:
    for Model, nomes in DOMINIOS.items():
        # Busca de uma vez os nomes que já existem nesta tabela (evita duplicar).
        existentes = {nome for (nome,) in db.query(Model.nome).all()}
        for nome in nomes:
            if nome not in existentes:
                db.add(Model(nome=nome))
                print(f"   + {Model.__tablename__}: {nome}")


def seed_admin(db) -> None:
    # Usa as constantes definidas lá em cima. Simples e à vista.
    if db.query(User).filter_by(username=ADMIN_USERNAME).first():
        print(f"   (admin '{ADMIN_USERNAME}' já existe — pulando)")
        return

    db.add(
        User(
            username=ADMIN_USERNAME,
            password_hash=hash_password(ADMIN_PASSWORD),  # guardamos o hash, nunca a senha pura
            nome=ADMIN_NOME,
            role="admin",
        )
    )
    print(f"   + admin criado: {ADMIN_USERNAME}")


def main() -> None:
    db = SessionLocal()
    try:
        print(">> Populando tabelas de domínio...")
        seed_dominios(db)
        print(">> Garantindo usuário admin...")
        seed_admin(db)
        db.commit()  # só agora grava tudo de fato no banco
        print("\n>> Seed concluído com sucesso!")
    finally:
        db.close()  # sempre fecha a sessão, mesmo se der erro


if __name__ == "__main__":
    main()
