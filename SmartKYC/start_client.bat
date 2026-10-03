@echo off
cd /d "%~dp0"
if exist "SmartKYC_Client.exe" (
  start "" "SmartKYC_Client.exe"
) else (
  echo Run the packaged SmartKYC folder, or use your development Python to run client.py.
  pause
)
