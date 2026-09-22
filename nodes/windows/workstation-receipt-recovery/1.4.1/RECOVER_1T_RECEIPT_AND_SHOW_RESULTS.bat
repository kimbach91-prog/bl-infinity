@echo off
setlocal
title DEUS 1T Workstation Receipt Recovery 1.4.1
echo ============================================================
echo  DEUS V5 WORKSTATION - 1T RECEIPT RECOVERY 1.4.1
echo ============================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RECOVER_1T_RECEIPT_AND_SHOW_RESULTS.ps1"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo [PASS] Recovery completed and readback verified.
) else (
  echo [FAIL] Recovery did not reach VERIFIED_DONE. See exact gate above.
)
echo.
pause
exit /b %RC%
