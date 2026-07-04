@echo off
REM ============================================================
REM  Inicia o Sistema de O.S. da Secao de Patrimonio SEM ATUALIZAR.
REM
REM  Use ESTE atalho no dia a dia (rede cabeada): sobe o servidor
REM  Reflex direto, sem tentar falar com o GitHub. Assim nao ha a
REM  espera do timeout que o firewall causaria.
REM
REM  Para ATUALIZAR o sistema, use "iniciar_patrimonio.bat" conectado
REM  ao 5G (so quando o desenvolvedor avisar que saiu versao nova).
REM
REM  Funciona em qualquer pasta/drive: "%~dp0" = pasta deste .bat.
REM ============================================================
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

REM --- Sobe a aplicacao direto, sem passar pelo atualizar.py ---
python -m reflex run
