@echo off
cd /d "%~dp0"
echo [1/3] PyInstaller kuruluyor...
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto hata
echo [2/3] Exe olusturuluyor (birkac dakika surebilir)...
python -m PyInstaller --noconfirm --onefile --noconsole --name GamepadStudio --collect-all vgamepad --collect-all pywinusb gamepad_studio.py
if errorlevel 1 goto hata
echo [3/3] Exe bu klasore kopyalaniyor...
copy /y dist\GamepadStudio.exe GamepadStudio.exe >nul
echo.
echo BITTI. Bu klasordeki GamepadStudio.exe dosyasina cift tikla.
echo (key_config.json ayni klasorde durmali.)
pause
exit /b 0
:hata
echo.
echo HATA olustu. Yukaridaki yaziyi kopyalayip bana gonder.
pause
exit /b 1
