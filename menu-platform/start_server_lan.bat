@echo off
cd /d "%~dp0"

echo Closing any server already using port 8000 or 8002...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":8000 "') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":8002 "') do taskkill /F /PID %%p >nul 2>&1

echo.
echo Starting server on your LAN IP - accessible from your phone too.
echo On the PC:    http://127.0.0.1:8000/
echo On the phone: http://192.168.1.71:8000/  (or just scan a QR code)
echo.
venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
pause
