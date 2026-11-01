@echo off
setlocal
title Simulasi ERP EBM
echo Membuka simulasi EBM. Biarkan jendela ini tetap terbuka.
set "EBM_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%EBM_PYTHON%" (
  echo Python runtime tidak ditemukan. Jalankan app/server.py dengan Python 3.
  pause
  exit /b 1
)
"%EBM_PYTHON%" -u "%~dp0app\server.py"
echo.
echo Server berhenti. Jika ada pesan kesalahan, salin pesan tersebut.
pause
