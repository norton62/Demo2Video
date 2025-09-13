@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ---------------------------------------------------------------
REM Keep window open when double-clicked (persistent console)
REM ---------------------------------------------------------------
if /I not "%~1"=="from_shell" (
  start "CS Demo Processor - Launcher" cmd /k "%~f0" from_shell
  exit /b
)

cls
echo ================================================================
echo == CS Demo Processor - Application Launcher
echo ================================================================
echo.

REM --- Resolve repo root ---
set "ROOT=%~dp0"

REM --- Verify app folder exists ---
if exist "%ROOT%cs-demo-processor" goto APP_OK
echo ERROR: 'cs-demo-processor' not found next to this script.
echo Put this .bat in the parent folder of cs-demo-processor\
goto DONE
:APP_OK

echo This will start all components.
echo Make sure you ran install.bat and setup_youtube_auth.py first.
echo.

REM ---------------------------------------------------------------
REM OBS path (stored in obs_path.txt next to this script)
REM ---------------------------------------------------------------
set "OBS_CFG=%ROOT%obs_path.txt"
set "OBS_EXE="

if exist "%OBS_CFG%" for /f "usebackq delims=" %%P in ("%OBS_CFG%") do set "OBS_EXE=%%P"
if defined OBS_EXE if exist "%OBS_EXE%" goto OBS_READY

REM Try default
set "OBS_DEFAULT=%ProgramFiles%\obs-studio\bin\64bit\obs64.exe"
if exist "%OBS_DEFAULT%" (
  set "OBS_EXE=%OBS_DEFAULT%"
  >"%OBS_CFG%" echo %OBS_EXE%
  echo Detected OBS: %OBS_EXE%
  goto OBS_READY
)

REM Prompt once
echo OBS not found in the default location.
echo If you want this launcher to start OBS, enter full path to obs64.exe
echo Example: C:\Program Files\obs-studio\bin\64bit\obs64.exe
set /p "OBS_EXE=Path to obs64.exe (leave blank to skip): "
if not defined OBS_EXE goto OBS_SKIP
if exist "%OBS_EXE%" (
  >"%OBS_CFG%" echo %OBS_EXE%
  echo Saved OBS path.
  goto OBS_READY
) else (
  echo The path does not exist. Skipping OBS auto-start.
  set "OBS_EXE="
  goto OBS_SKIP
)

:OBS_READY
echo Will start OBS from: %OBS_EXE%
:OBS_SKIP
echo.

REM ---------------------------------------------------------------
REM Ensure NVM LTS in this shell (harmless if NVM missing)
REM ---------------------------------------------------------------
where nvm >nul 2>&1 && (call nvm use lts >nul 2>&1)

REM ---------------------------------------------------------------
REM [1/4] Start CSDM dev server (own window, stays open)
REM ---------------------------------------------------------------
echo [1/4] Starting the CS Demo Manager dev server...
start "CSDM Dev Server" /D "%ROOT%cs-demo-processor\csdm-fork" cmd /k node scripts\develop-cli.mjs
echo   Launched window: CSDM Dev Server
echo.

REM ---------------------------------------------------------------
REM [2/4] Start main Python app (own window, stays open)
REM ---------------------------------------------------------------
echo [2/4] Starting the main Python application...
start "CS Demo Processor" /D "%ROOT%cs-demo-processor" cmd /k python main.py
echo   Launched window: CS Demo Processor
echo.

REM ---------------------------------------------------------------
REM [3/4] Start OBS if path is set and exists
REM ---------------------------------------------------------------
if not defined OBS_EXE goto NO_OBS
if not exist "%OBS_EXE%" goto NO_OBS
for %%D in ("%OBS_EXE%") do set "OBS_DIR=%%~dpD"
echo [3/4] Starting OBS Studio...
start "OBS Studio" /D "%OBS_DIR%" "%OBS_EXE%"
echo   Launched window: OBS Studio
echo   Tip: In OBS, open Tools -> WebSocket Server Settings (port 4455).
echo.
goto OBS_OK
:NO_OBS
echo [3/4] OBS not started by launcher (no valid path configured).
echo.
:OBS_OK

REM ---------------------------------------------------------------
REM [4/4] Open the web UI after a short delay
REM ---------------------------------------------------------------
echo [4/4] Waiting 5 seconds for the web server to start...
timeout /t 5 /nobreak >nul
echo Opening http://localhost:5001
start "" "http://localhost:5001"
echo.

echo ================================================================
echo == Launcher finished. This window will remain open.
echo ================================================================
echo.
:DONE
endlocal