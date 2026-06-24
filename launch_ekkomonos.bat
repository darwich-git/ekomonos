@echo off
echo Iniciando EKKOMONOS con auto-snap...

REM Start AutoHotkey script
start "" "%~dp0AutoHotkey.exe" "%~dp0ekkomonos_snap.ahk"

REM Wait a moment
timeout /t 1 /nobreak >nul

REM Launch EKKOMONOS
python "%~dp0main.py"
