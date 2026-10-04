@echo off
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

python atualizar.py

python -m reflex run
