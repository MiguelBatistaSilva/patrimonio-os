@echo off
REM ============================================================
REM  Inicia o Sistema de O.S. da Secao de Patrimonio (producao).
REM  Deixe este arquivo na RAIZ do projeto. Ele funciona em
REM  qualquer pasta/drive porque "%~dp0" = a pasta deste .bat.
REM ============================================================
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
python -m reflex run --env prod
