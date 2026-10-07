@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch-Portal.ps1"
if errorlevel 1 pause
