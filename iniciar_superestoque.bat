@echo off
cd /d "%~dp0"
start "SuperEstoque Backend" cmd /k "python backend\server.py"
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8000/
