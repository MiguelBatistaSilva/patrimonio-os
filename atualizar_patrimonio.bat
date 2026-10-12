@echo off
rem Apenas ATUALIZA a aplicacao (baixa a versao nova do GitHub e aplica).
rem Use com a aplicacao FECHADA e numa rede que acesse o GitHub (ex.: 5G).
rem Depois de atualizar, inicie pelo iniciar_patrimonio.bat.
cd /d "%~dp0"

echo ============================================================
echo  Atualizar o Sistema de O.S. - Secao de Patrimonio
echo ============================================================
echo.
echo  1. A aplicacao precisa estar FECHADA.
echo  2. O computador precisa estar numa rede que acesse o GitHub.
echo.
pause

call ".venv\Scripts\activate.bat"
python atualizar.py

echo.
echo ============================================================
echo  Fim. Veja acima se a atualizacao foi concluida.
echo  Para usar o sistema, abra o iniciar_patrimonio.bat.
echo ============================================================
pause
