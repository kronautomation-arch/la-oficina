@echo off
echo Starting KRON Telegram Bot...
cd /d "%~dp0"
call "%USERPROFILE%\Documents\CLAUDE CODE\campana-tenis\venv\Scripts\activate.bat"
python tools\core\telegram_bot.py
pause
