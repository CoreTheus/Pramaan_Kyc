@echo off
cd /d "%~dp0"
if not exist "SmartKYC_Server.exe" (
  echo Use setup.bat from the packaged SmartKYC folder.
  pause
  exit /b 1
)
SmartKYC_Server.exe --setup
pause
