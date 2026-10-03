@echo off
cd /d "%~dp0"
if exist "SmartKYC_Server.exe" (
  SmartKYC_Server.exe
) else (
  echo Run the packaged SmartKYC folder, or use your development Python to run server.py.
  pause
)
