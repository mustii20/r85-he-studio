@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw gamepad_studio.py & exit /b)
where pyw >nul 2>nul && (start "" pyw gamepad_studio.py & exit /b)
echo Python bulunamadi.
echo Python'u kurarken "Add python.exe to PATH" kutusunu isaretlemelisin.
pause
