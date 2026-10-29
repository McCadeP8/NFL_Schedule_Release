@echo off
REM Desktop launcher: start the NHL State Lab server if needed, then open the browser.
cd /d "%~dp0"
curl -s -o nul http://localhost:8517/_stcore/health
if errorlevel 1 (
    start "NHL State Lab server" /min ".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true --server.port 8517
    for /l %%i in (1,1,30) do (
        timeout /t 1 /nobreak >nul
        curl -s -o nul http://localhost:8517/_stcore/health && goto open
    )
)
:open
start "" http://localhost:8517
