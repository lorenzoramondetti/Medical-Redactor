
@echo off
setlocal

REM --- PRIVACY & PORTABILITY CONFIG ---
REM Prevent Python from writing .pyc files to disk (Zero-Trace)
set PYTHONDONTWRITEBYTECODE=1

REM Set the Title
title Medical Redactor Ultimate - Portable

REM Check for Portable Python folder
IF EXIST "python\python.exe" (
    echo [INFO] Found Portable Python. Launching...
    set "PYTHON_EXE=python\python.exe"
) ELSE (
    echo [INFO] Portable Python not found. Using System Python...
    set "PYTHON_EXE=python"
)

REM --- LAUNCH APPLICATION ---
echo Starting Medical Redactor...
echo Please wait for the browser to open.
echo.

"%PYTHON_EXE%" -m streamlit run src/main.py --browser.gatherUsageStats=false --server.runOnSave=false

REM --- EXIT ---
pause
