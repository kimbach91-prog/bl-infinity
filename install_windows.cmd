@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install --disable-pip-version-check --no-index --find-links wheelhouse\windows -r requirements.lock
if errorlevel 1 exit /b 1
set PYTHONDONTWRITEBYTECODE=1
.venv\Scripts\python.exe arc3_offline.py smoke --root . --seeds 0,1,2 --steps 8
if errorlevel 1 exit /b 1
echo Offline environment smoke completed. This is NOT a solver benchmark or submission.
