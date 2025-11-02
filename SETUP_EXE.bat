@echo off
COLOR 0A
cls
echo ============================================
echo   REMOTE WEBCAM - QUICK SETUP
echo ============================================
echo.
echo This will:
echo  1. Copy RemoteWebcam.exe to Program Files
echo  2. Setup auto-start on boot
echo  3. Start service now
echo.
echo Requirements:
echo  - RemoteWebcam.exe (this folder)
echo  - ngrok.exe (Microsoft Store or download)
echo.
pause

REM Check Admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Run as Administrator!
    pause
    exit /b 1
)

SET SCRIPT_DIR=%~dp0
SET INSTALL_DIR=%ProgramFiles%\RemoteWebcam
SET STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

echo.
echo [1/3] Installing files...

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy "%SCRIPT_DIR%RemoteWebcam.exe" "%INSTALL_DIR%\" >nul

echo [OK] Files installed

echo.
echo [2/3] Setting up auto-start...

REM Create VBScript to run EXE silently on boot
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run """%INSTALL_DIR%\RemoteWebcam.exe""", 0, False
) > "%STARTUP_DIR%\RemoteWebcam.vbs"

echo [OK] Auto-start configured

echo.
echo [3/3] Starting service...

start "" "%INSTALL_DIR%\RemoteWebcam.exe"
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo   SETUP COMPLETE!
echo ============================================
echo.
echo Service running in background
echo Will auto-start on every boot
echo.
echo IMPORTANT: Make sure ngrok is installed!
echo  - Microsoft Store: Search "ngrok"
echo  - OR download from: https://ngrok.com/download
echo.
echo Check mobile app - device should be ONLINE!
echo.
echo ============================================
pause
