@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe. See docs\sheets-windows.md.
  popd
  exit /b 2
)
".venv\Scripts\python.exe" -X utf8 "%~dp0scripts\sheet-files.py" %*
set "sheetExit=%ERRORLEVEL%"
popd
exit /b %sheetExit%
