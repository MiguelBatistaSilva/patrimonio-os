"""A "ponte" entre as plantas (models/*.py) e o banco real (PostgreSQL).

Rode este script UMA vez para criar todas as tabelas no banco `patrimonio`:

    ./.venv/Scripts/python.exe create_tables.py

O que acontece por baixo:
1. `import models` carrega TODOS os modelos -> todas as tabelas se registram em Base.metadata.
2. `Base.metadata.create_all(engine)` percorre esse mapa e envia um `CREATE TABLE ...`
   para cada tabela que AINDA NÃO existir (ele nunca apaga nem altera o que já existe).

Como o engine está com echo=True, você verá o SQL exato saindo no terminal — é o
PostgreSQL recebendo cada CREATE TABLE. É a planta virando casa, ao vivo.
"""

import models  # noqa: F401  (importado pelo efeito colateral: registra as tabelas em Base.metadata)
from services.database import Base, engine


def main() -> None:
    print(">> Criando as tabelas no banco (as que já existirem são ignoradas)...\n")
    Base.metadata.create_all(engine)

    # Lista o que o SQLAlchemy conhece, para você conferir o resultado.
    print("\n>> Pronto! Tabelas registradas:")
    for nome in sorted(Base.metadata.tables):
        print(f"   - {nome}")


if __name__ == "__main__":
    main()
