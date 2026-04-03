@echo off
cd /d "%~dp0"

echo ==========================================
echo   Kocaeli News - Scraper pipeline
echo ==========================================
echo.
echo Activating virtual environment...
call D:\Installed\venvs\kocaeli-news\Scripts\activate

echo Running scraper (last 3 calendar days by default)...
echo.

cd backend
python scraper_runner.py

pause
