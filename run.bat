@echo off
title Auto Publish Content Pipeline
cls
echo =====================================================================
echo          Auto Publish Content Pipeline - Quick Launcher
echo =====================================================================
echo.

REM 1. Check Python installation
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b
)

REM 2. Install / check requirements
echo [1/3] Checking and installing dependencies...
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install required Python packages.
    pause
    exit /b
)

REM 3. Google Drive Login Check
if not exist "token.json" (
    echo.
    echo =====================================================================
    echo [2/3] FIRST-TIME SETUP: Connect your Google Drive
    echo =====================================================================
    echo If your browser does not open automatically, copy the link shown.
    echo.
    python authenticate.py
    if %ERRORLEVEL% neq 0 (
        echo.
        echo [WARNING] Login did not complete. You can also log in from inside the app sidebar.
    )
) else (
    echo [2/3] Google Drive authorization found.
)

REM 4. Launch Streamlit app
echo.
echo =====================================================================
echo [3/3] Launching App...
echo If your browser does not open automatically, open Helium and go to:
echo   http://localhost:8501
echo =====================================================================
echo.

REM Try opening default browser to the URL
start http://localhost:8501

REM Run Streamlit via python -m (guaranteed to work even if streamlit.exe is not in PATH)
python -m streamlit run app.py

pause
