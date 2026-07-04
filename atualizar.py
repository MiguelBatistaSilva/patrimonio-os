"""
atualizar.py — Auto-atualizador do Sistema de O.S. da Seção de Patrimônio.

O QUE FAZ (roda ANTES do 'reflex run', chamado pelo iniciar_patrimonio.bat):
  1. Descobre a versão LOCAL (lendo version.py) e a REMOTA (version.json no GitHub).
  2. Se a remota for maior, baixa o .zip do repositório e troca os arquivos por cima,
     PRESERVANDO .env, banco, .venv e os dados locais.
  3. Faz um backup da versão anterior em _backup/ antes de trocar (rede de segurança).
  4. Roda pip install e alembic upgrade (caso a atualização traga libs/migrations novas).

PRINCÍPIO DE OURO — FAIL-OPEN: se QUALQUER coisa der errado (sem internet, GitHub fora,
erro de download), o script DESISTE em silêncio e deixa o app abrir normalmente.
Atualizar nunca pode impedir o chefe de usar o sistema.

Usa somente a biblioteca padrão do Python (sem 'requests'), para não depender de nada
que precise ser instalado antes de o updater rodar.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

# ─── Configuração ────────────────────────────────────────────────────────────
REPO = "MiguelBatistaSilva/patrimonio-os"
VERSION_URL = f"https://raw.githubusercontent.com/{REPO}/main/version.json"
ZIP_URL = f"https://github.com/{REPO}/archive/refs/heads/main.zip"

BASE_DIR = Path(__file__).resolve().parent
VENV_PY = BASE_DIR / ".venv" / "Scripts" / "python.exe"
BACKUP_DIR = BASE_DIR / "_backup"
LOG_FILE = BASE_DIR / "_update.log"

# Pastas que NUNCA são copiadas (nem no update, nem no backup): pesadas ou de runtime.
EXCLUIR_DIRS = [".venv", ".web", ".states", "_backup", ".git", "__pycache__"]
# Arquivos protegidos de sobrescrita:
#   .env                    -> segredos locais (senha do banco), nunca tocar
#   iniciar_patrimonio.bat  -> sobrescrever um .bat EM EXECUÇÃO corrompe o Windows
#   _update.log             -> nosso próprio log
EXCLUIR_FILES = [".env", "iniciar_patrimonio.bat", "_update.log"]

UA = {"User-Agent": "patrimonio-updater"}


def log(msg: str) -> None:
    """Imprime na tela E grava em _update.log (para diagnosticar na máquina do chefe)."""
    linha = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(linha)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass


def ler_versao_local() -> str:
    """Lê VERSION de version.py sem importar (evita dor de cabeça com sys.path)."""
    version_file = BASE_DIR / "version.py"
    try:
        for linha in version_file.read_text(encoding="utf-8").splitlines():
            if linha.strip().startswith("VERSION"):
                return linha.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "0.0.0"


def ler_versao_remota() -> str | None:
    """Busca o version.json publicado no GitHub. Devolve None se não conseguir."""
    req = urllib.request.Request(VERSION_URL, headers=UA)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8")).get("version")


def versao_maior(remota: str, local: str) -> bool:
    """True se 'remota' > 'local' comparando 1.2.3 como tupla (1, 2, 3)."""
    try:
        r = tuple(int(x) for x in remota.strip().split("."))
        l = tuple(int(x) for x in local.strip().split("."))
        return r > l
    except Exception:
        return False


def baixar_zip(destino: Path) -> None:
    """Baixa o zip do branch main para 'destino'."""
    req = urllib.request.Request(ZIP_URL, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(destino, "wb") as f:
        shutil.copyfileobj(r, f)


def _robocopy(origem: Path, destino: Path, excluir_arquivos: bool) -> int:
    """Copia origem->destino de forma ADITIVA (sem /MIR e sem /PURGE: nunca apaga).
    Devolve o código do robocopy (0-7 = sucesso; >=8 = erro real)."""
    cmd = ["robocopy", str(origem), str(destino), "/E",
           "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:2", "/W:2"]
    for d in EXCLUIR_DIRS:
        cmd += ["/XD", d]
    if excluir_arquivos:
        for f in EXCLUIR_FILES:
            cmd += ["/XF", f]
    return subprocess.run(cmd, capture_output=True, text=True).returncode


def fazer_backup() -> None:
    """Guarda o estado atual (inclui .env) em _backup/, substituindo o backup anterior."""
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR, ignore_errors=True)
    BACKUP_DIR.mkdir(exist_ok=True)
    # No backup NÃO excluímos arquivos (queremos guardar o .env também).
    _robocopy(BASE_DIR, BACKUP_DIR, excluir_arquivos=False)


def pos_atualizacao() -> None:
    """Depois de trocar os arquivos: instala libs novas e aplica migrations."""
    py = str(VENV_PY) if VENV_PY.exists() else sys.executable

    log("Verificando dependências (pip install -r requirements.txt)...")
    subprocess.run([py, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
                   cwd=str(BASE_DIR))

    log("Aplicando migrations (alembic upgrade head)...")
    subprocess.run([py, "-m", "alembic", "upgrade", "head"], cwd=str(BASE_DIR))


def main() -> None:
    tmp = None
    try:
        local = ler_versao_local()
        remota = ler_versao_remota()

        if not remota:
            log("Não foi possível ler a versão remota. Seguindo sem atualizar.")
            return
        if not versao_maior(remota, local):
            log(f"Já está na versão mais recente ({local}).")
            return

        log(f"Nova versão disponível: {remota} (local: {local}). Baixando...")
        tmp = Path(tempfile.mkdtemp())
        zip_path = tmp / "update.zip"
        baixar_zip(zip_path)

        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        zip_path.unlink()

        # O zip do GitHub extrai numa subpasta tipo "patrimonio-os-main/".
        subdirs = [d for d in tmp.iterdir() if d.is_dir()]
        if not subdirs:
            log("Zip extraído sem a pasta esperada. Abortando atualização.")
            return
        origem = subdirs[0]

        log("Fazendo backup da versão atual em _backup/...")
        fazer_backup()

        log("Aplicando os novos arquivos...")
        codigo = _robocopy(origem, BASE_DIR, excluir_arquivos=True)
        if codigo >= 8:
            log(f"ERRO no robocopy (código {codigo}). Restaure de _backup/ se necessário.")
            return

        pos_atualizacao()
        log(f"Atualização para {remota} concluída com sucesso.")

    except Exception as e:
        # Fail-open: nunca impede o app de abrir.
        log(f"Atualização ignorada por erro: {e}")
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
