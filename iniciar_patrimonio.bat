@echo off
rem Apenas INICIA a aplicacao. Para atualizar, use o atualizar_patrimonio.bat
rem (com a aplicacao fechada).
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

python -m reflex run
