@echo off
REM XploClone — one-click install (Windows).
REM Runs install.ps1. If PowerShell blocks it, run:
REM   powershell -ExecutionPolicy Bypass -File install.ps1
REM See install.ps1 for options (-Mode cpu, -Mode gpu, -CheckOnly).
powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
