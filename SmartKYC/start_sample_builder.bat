@echo off
cd /d "%~dp0"
if exist "SmartKYC_SampleBuilder.exe" (
  start "" "SmartKYC_SampleBuilder.exe"
) else (
  echo SmartKYC_SampleBuilder.exe was not found.
  pause
)
