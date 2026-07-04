@echo off
REM ============================================================
REM  Inicia o Sistema de O.S. da Secao de Patrimonio COM ATUALIZACAO.
REM   1) Verifica/aplica atualizacoes (atualizar.py)
REM   2) Sobe o servidor Reflex
REM
REM  Use ESTE atalho apenas no DIA DE ATUALIZAR, conectado ao 5G
REM  (o firewall da rede cabeada bloqueia o GitHub e o pip). No dia
REM  a dia normal, use "iniciar_sem_atualizar.bat".
REM
REM  Funciona em qualquer pasta/drive: "%~dp0" = pasta deste .bat.
REM ============================================================
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

REM --- Passo 1: auto-atualizacao (fail-open: nunca impede o app de abrir) ---
python atualizar.py

REM --- Passo 2: inicia a aplicacao ---
python -m reflex run
