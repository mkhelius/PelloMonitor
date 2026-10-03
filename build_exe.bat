@echo off
echo === Pello Monitor FREE - budowanie PelloMonitor.exe ===
python -m pip install --upgrade pyinstaller pystray pillow keyring
echo.
echo Generowanie ikony pliku (plomien)...
python pello_tray.py pello.ico
echo.
python -m PyInstaller --onefile --windowed --name PelloMonitor --icon pello.ico --hidden-import=pystray._win32 --hidden-import=keyring.backends.Windows pello_monitor.py
echo.
echo Gotowe! Plik znajdziesz w: dist\PelloMonitor.exe
pause
