@echo off
REM ============================================================
REM  Inicia o Sistema de O.S. da Secao de Patrimonio.
REM   1) Verifica/aplica atualizacoes (atualizar.py)
REM   2) Sobe o servidor Reflex
REM  Funciona em qualquer pasta/drive: "%~dp0" = pasta deste .bat.
REM ============================================================
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

REM --- Passo 1: auto-atualizacao (fail-open: nunca impede o app de abrir) ---
python atualizar.py

REM --- Passo 2: inicia a aplicacao ---
python -m reflex run
