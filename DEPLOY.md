# Deploy — Sistema de O.S. (Seção de Patrimônio)

Guia para instalar na **máquina-host** (PC do chefe) e deixar acessível pelos colegas na rede.
Conceito: só o PC do chefe RODA o app; os colegas só abrem no navegador `http://NOME-DO-PC:3000`.

---

## Fase 0 — Na SUA máquina (antes de ir)

- [ ] Testar o build de produção aqui: `python -m reflex run --env prod` → abrir http://localhost:3000.
- [ ] (Opcional) Levar os dados atuais: gerar um dump
      `& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -p 5433 -U patrimonio_app -d patrimonio -f patrimonio.sql`
      (Se for começar limpo lá, ignore — o seed recria o essencial.)
- [ ] Copiar a pasta do projeto **SEM**: `.venv/`, `.web/`, `__pycache__/`, `bibliotecas/` (opcional).
      **NÃO** levar o `.env` (a porta e o APP_HOST mudam — recria no passo 4).

---

## Fase 1 — Na máquina do chefe

### 1. Python
- [ ] Instalar **Python 3.11** (marcar "Add Python to PATH").
- [ ] Conferir: `python --version`

### 2. Projeto + dependências  ⚡ (com o 5G ligado)
- [ ] Colar o projeto em `C:\patrimonio` (ou onde preferir).
- [ ] Na pasta do projeto: `python -m venv .venv`
- [ ] Ativar: `.venv\Scripts\activate`
- [ ] `pip install -r requirements.txt`

### 3. PostgreSQL
- [ ] Instalar o PostgreSQL. **Anotar a PORTA** (instalação nova costuma ser **5432**).
- [ ] No psql como `postgres`, criar role e banco:
  ```sql
  CREATE ROLE patrimonio_app LOGIN PASSWORD 'A_SENHA_QUE_VOCE_QUISER';
  CREATE DATABASE patrimonio OWNER patrimonio_app;
  ```
- [ ] (Opcional) Restaurar o dump da Fase 0:
      `psql -p 5432 -U patrimonio_app -d patrimonio -f patrimonio.sql`

### 4. Arquivo .env
- [ ] Criar `.env` na raiz (copiar de `.env.example`) e preencher:
  ```
  DATABASE_URL=postgresql+psycopg2://patrimonio_app:A_SENHA@localhost:5432/patrimonio
  APP_HOST=NOME-DO-PC
  ```
  - Ajustar a **PORTA** (5432 se foi instalação nova). Senha com `@` → `%40`.
  - `NOME-DO-PC`: descobrir com o comando `hostname`.
  - Sem a env var global `PGSSLMODE`, **não** precisa do `?sslmode=disable`.

### 5. Banco: estrutura + dados iniciais  (pular se restaurou o dump no passo 3)
- [ ] `python create_tables.py`
- [ ] `python -m alembic stamp head`   ← marca o banco como já na última migration
- [ ] Conferir as credenciais do admin no topo do `seed.py`, então: `python seed.py`

### 6. Primeira execução  ⚡ (AINDA no 5G — baixa o frontend)
- [ ] `python -m reflex run --env prod`  → na 1ª vez baixa o bun/Node e monta o frontend.
- [ ] Confirmar abrindo **http://localhost:3000** na própria máquina.
      ⚠️ O Reflex vai dizer que está em `http://0.0.0.0:3000` — isso é normal (`0.0.0.0`
      = "escuta em todas as interfaces"). Você NÃO acessa por `0.0.0.0`; use `localhost`
      na própria máquina, e `http://NOME-DO-PC:3000` nas outras.
- [ ] Parar (Ctrl+C). **Agora pode tirar o 5G e voltar o cabo de rede.**

### 7. Acesso pela rede
- [ ] Conferir nome/IP: `hostname` e `ipconfig`. Garantir que bate com `APP_HOST` no `.env`.
- [ ] Subir de novo: `python -m reflex run --env prod`
- [ ] De **outro PC**, abrir no navegador: `http://NOME-DO-PC:3000`
  - Abriu e logou? 🎉 Pular o passo 8.
  - Não abriu? → passo 8 (firewall).

### 8. Firewall  (só se o passo 7 não abrir de outra máquina)
- [ ] Abrir um terminal **como Administrador** e rodar:
  ```
  netsh advfirewall firewall add rule name="Patrimonio" dir=in action=allow protocol=TCP localport=3000,8000
  ```
- [ ] Testar de novo do outro PC.

### 9. Iniciar sozinho ao ligar  (opcional, recomendado)
- [ ] O arquivo `iniciar_patrimonio.bat` já vem no projeto (na raiz) e funciona em
      qualquer pasta/drive (usa `%~dp0`). Não precisa editar.
- [ ] Testar dando duplo-clique nele → deve subir o app.
- [ ] Win+R → `shell:startup` → colar um **atalho** do `iniciar_patrimonio.bat`.
- [ ] ⚠️ Lembrete: a aplicação fica no ar enquanto o chefe estiver **logado**; para quando ele desliga/desloga.

---

## Resolução de problemas

- **Tela abre mas fica "carregando"/não conecta de outro PC:** `APP_HOST` errado no `.env`
  (tem que ser o nome/IP do PC do chefe), ou falta liberar o firewall (passo 8).
- **Erro de conexão com o banco:** conferir PORTA e senha na `DATABASE_URL`.
- **Mudou o nome/IP do PC do chefe:** atualizar `APP_HOST` no `.env` e reiniciar o app.
