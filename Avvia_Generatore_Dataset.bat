@echo off
title Medical Redactor - Generatore Dataset Sintetico (GUI)

:: Usa pythonw.exe (launcher senza console) per aprire la GUI Tkinter
:: Nessuna finestra nera apparira' durante l'utilizzo normale

setlocal

:: Ricerca python.exe nel PATH
for /f "delims=" %%i in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%i"
    goto :found_python
)

:not_found
echo [ERRORE] Python non e stato trovato sul sistema.
echo Si prega di installare Python 3.11+ da https://www.python.org/downloads/
echo Assicurarsi di spuntare "Add Python to PATH" durante l'installazione.
pause
exit /b 1

:found_python
:: Costruisce il percorso di pythonw.exe nella stessa directory di python.exe
set "PYTHONW_EXE=%PYTHON_EXE:python.exe=pythonw.exe%"

:: Verifica che pythonw.exe esista
if not exist "%PYTHONW_EXE%" (
    set "PYTHONW_EXE=%PYTHON_EXE%"
)

:: Avvia la GUI senza finestra console
start "" "%PYTHONW_EXE%" "%~dp0synthetic_dataset\gui_generator.py"

endlocal
exit /b 0
