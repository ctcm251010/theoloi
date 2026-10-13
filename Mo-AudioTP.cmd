@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Khong tim thay Python environment cua workspace. Xem SETUP.md.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -X utf8 "%~dp0scripts\start-windows-local.py"
if errorlevel 1 pause
