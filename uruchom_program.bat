@echo off
rem Uruchamia program bez budowania pliku .exe (wymaga zainstalowanego Pythona)
python -m pip install --quiet pystray pillow keyring
python pello_monitor.py
if errorlevel 1 pause
