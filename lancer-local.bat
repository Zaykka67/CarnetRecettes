@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (
  echo Création de l'environnement Python...
  python -m venv .venv
  .venv\Scripts\python -m pip install -q -r requirements.txt
)
if exist .env (
  for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
)
set DATA_DIR=%~dp0data
echo Carnet de recettes : http://127.0.0.1:8000
start "" http://127.0.0.1:8000
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
