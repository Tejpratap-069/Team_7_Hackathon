@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo First run the setup commands in README.md to create .venv and install requirements.
  pause
  exit /b 1
)
.venv\Scripts\python.exe app.py
pause
