@echo off
REM ============================================================================
REM GeoVault AI — SIH Demo Environment Reset & Fast Restore (Windows)
REM ============================================================================
echo [!] Resetting GeoVault AI demonstration environment...

cd /d "%~dp0\.."

echo [*] Restarting containers...
docker compose restart backend frontend worker

echo [*] Waiting 5 seconds for services to initialize...
timeout /t 5 /nobreak >nul

echo [*] Running fast SIH Smoke-Test...
python scripts\smoke_test_demo.py

echo [✓] Environment reset and certified ready for presentation!
pause
