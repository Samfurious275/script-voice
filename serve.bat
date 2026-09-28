@echo off
REM Opens the script-to-voiceover page in your browser.
REM First run creates the environment; after that it starts in seconds.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  set PY=
  py -3 --version >nul 2>&1 && set PY=py -3
  if not defined PY (
    python --version >nul 2>&1 && set PY=python
  )
  if not defined PY (
    echo.
    echo Python 3 is required but was not found.
    echo Install it from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" in the installer, then run this again.
    pause
    exit /b 1
  )
  echo Setting up ^(one minute, once^)...
  %PY% -m venv .venv || goto :failed
  .venv\Scripts\python.exe -m pip install --upgrade pip >nul || goto :failed
  .venv\Scripts\python.exe -m pip install -r requirements.txt || goto :failed
)

.venv\Scripts\python.exe serve.py %*
if errorlevel 1 pause
exit /b 0

:failed
echo.
echo Setup failed. The messages above say why.
pause
exit /b 1
