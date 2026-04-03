@echo off
cd /d "%~dp0"

echo ==========================================
echo   Kocaeli News Map - Startup Script
echo ==========================================
echo.
echo [1/2] Activating Virtual Environment...
call D:\Installed\venvs\kocaeli-news\Scripts\activate

echo [2/2] Starting Uvicorn Server on http://127.0.0.1:8000/app/
echo.
echo (Keep this window open to keep the site alive)
echo (Press Ctrl+C to stop the server)
echo.

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

pause
