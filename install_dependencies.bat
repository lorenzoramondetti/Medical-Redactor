@echo off
setlocal

REM Set the Title
title Medical Redactor - Install Dependencies

echo ===================================================
echo   Medical Redactor Ultimate - Portable Installer
echo ===================================================
echo.
echo Installing required dependencies to the portable Python environment...
echo.

REM Check for Portable Python folder
IF EXIST "python\python.exe" (
    set "PYTHON_EXE=python\python.exe"
    set "PIP_EXE=python\Scripts\pip.exe"
) ELSE (
    echo [ERROR] Portable Python not found in the 'python' folder!
    echo Please make sure the 'python' folder exists in the same directory as this script.
    pause
    exit /b 1
)

REM Check if pip exists, if not, try to install it using module
IF NOT EXIST "%PIP_EXE%" (
    echo [INFO] Pip not found in Scripts folder. Trying to run python -m pip...
    "%PYTHON_EXE%" -m pip install --upgrade pip
)

REM Install dependencies
echo [INFO] Installing packages from requirements.txt...
"%PYTHON_EXE%" -m pip install -r requirements.txt

echo.
echo ===================================================
echo   Installation Complete!
echo   You can now run 'start_portable.bat'
echo ===================================================
pause
