@echo off
cd /d "%~dp0"
echo [1/3] Gerekli paketler kontrol ediliyor...
python -m pip install --upgrade pyinstaller pywebview
if errorlevel 1 goto hata
echo [2/3] R85Studio.exe olusturuluyor (birkac dakika surebilir)...
python -m PyInstaller --noconfirm --onefile --noconsole --name R85Studio ^
  --collect-all vgamepad --collect-all pywinusb --collect-all webview ^
  --collect-all pythonnet --collect-all clr_loader ^
  --add-data "ui;ui" r85_studio.py
if errorlevel 1 goto hata
echo [3/3] Exe bu klasore kopyalaniyor...
copy /y dist\R85Studio.exe R85Studio.exe >nul
echo.
echo BITTI. Bu klasordeki R85Studio.exe dosyasina cift tikla.
echo (key_config.json ve gamepad_profiles.json ayni klasorde durmali.)
pause
exit /b 0
:hata
echo.
echo HATA olustu. Yukaridaki yaziyi kopyalayip bana gonder.
pause
exit /b 1
