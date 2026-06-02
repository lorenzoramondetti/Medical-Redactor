@echo off
title Medical Redactor - Generatore Dataset Sintetico (GUI)

:: Usa il percorso assoluto di pythonw.exe per avviare la GUI senza finestra nera
:: pythonw.exe = launcher Python senza console, ideale per applicazioni grafiche Tkinter

setlocal

:: Percorso di pythonw.exe (rilevato automaticamente dalla stessa cartella di python.exe)
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
    :: Fallback a python.exe normale se pythonw non trovato
    set "PYTHONW_EXE=%PYTHON_EXE%"
)

:: Avvia la GUI senza finestra console (start /B = processo detached)
start "" "%PYTHONW_EXE%" "%~dp0gui_generator.py"

endlocal
exit /b 0
