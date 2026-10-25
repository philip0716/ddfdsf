@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto failed
)
.venv\Scripts\python.exe server.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo Start fehlgeschlagen. Python 3.12 und die Anleitung in README.md pruefen.
pause
exit /b 1
