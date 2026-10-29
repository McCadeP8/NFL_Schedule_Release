@echo off
REM Nightly NHL State Lab update (run by Windows Task Scheduler).
cd /d "%~dp0"
if not exist logs mkdir logs
echo ==== %DATE% %TIME% ==== >> logs\nightly_update.log
".venv\Scripts\python.exe" -W ignore -m nhl_state_lab.pipeline --season 20262027 --game-types 1 2 3 --incremental >> logs\nightly_update.log 2>&1
