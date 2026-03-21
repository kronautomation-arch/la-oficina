@echo off
cd /d "%~dp0"
call venv\Scripts\activate 2>nul
python tools\core\sync_to_github.py
