@echo off
COLOR 0A
cls
echo ============================================
echo   REMOTE WEBCAM - ONE-CLICK INSTALLER
echo ============================================
echo.
echo This will automatically:
echo  [1] Detect Python (any location)
echo  [2] Detect ngrok (Store/Download/Portable)
echo  [3] Install all libraries
echo  [4] Setup auto-start on boot
echo  [5] Connect to cloud server
echo.
echo Smart detection - no PATH required!
echo.
pause

REM ============================================
REM Check Administrator
REM ============================================
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ERROR: Administrator rights required!
    echo Right-click this file and select "Run as Administrator"
    pause
    exit /b 1
)

SET SCRIPT_DIR=%~dp0
SET INSTALL_DIR=%ProgramFiles%\RemoteWebcam
SET STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

echo.
echo ============================================
echo [1/6] Detecting Python...
echo ============================================

SET PYTHON_CMD=

REM Check PATH first
python --version >nul 2>&1
if %errorLevel% equ 0 (
    SET PYTHON_CMD=python
    echo [OK] Python in PATH
    python --version
    goto :python_found
)

REM Check common AppData locations
for %%v in (313 312 311 310 39 38) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe" (
        SET "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe"
        echo [OK] Found: !PYTHON_CMD!
        "!PYTHON_CMD!" --version
        goto :python_found
    )
)

REM Check Program Files
for %%v in (313 312 311 310 39 38) do (
    if exist "%ProgramFiles%\Python%%v\python.exe" (
        SET "PYTHON_CMD=%ProgramFiles%\Python%%v\python.exe"
        echo [OK] Found: !PYTHON_CMD!
        "!PYTHON_CMD!" --version
        goto :python_found
    )
)

echo [ERROR] Python not found!
echo Please install Python from: https://www.python.org/downloads/
pause
exit /b 1

:python_found

echo.
echo ============================================
echo [2/6] Detecting ngrok...
echo ============================================

SET NGROK_CMD=

REM Check portable folder
if exist "%SCRIPT_DIR%ngrok.exe" (
    SET "NGROK_CMD=%SCRIPT_DIR%ngrok.exe"
    echo [OK] Found in portable folder
    goto :ngrok_found
)

REM Check Microsoft Store location
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\ngrok.exe" (
    SET "NGROK_CMD=%LOCALAPPDATA%\Microsoft\WindowsApps\ngrok.exe"
    echo [OK] Found Microsoft Store version
    goto :ngrok_found
)

REM Check PATH
ngrok version >nul 2>&1
if %errorLevel% equ 0 (
    SET NGROK_CMD=ngrok
    echo [OK] Found in PATH
    goto :ngrok_found
)

REM Check Downloads
if exist "%USERPROFILE%\Downloads\ngrok.exe" (
    SET "NGROK_CMD=%USERPROFILE%\Downloads\ngrok.exe"
    echo [OK] Found in Downloads
    goto :ngrok_found
)

echo [ERROR] ngrok not found!
echo Install from Microsoft Store OR download from ngrok.com
pause
exit /b 1

:ngrok_found

echo.
echo ============================================
echo [3/6] Installing files...
echo ============================================

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

copy "%SCRIPT_DIR%main.py" "%INSTALL_DIR%\" >nul
copy "%SCRIPT_DIR%ngrok_helper.py" "%INSTALL_DIR%\" >nul
copy "%SCRIPT_DIR%start_ngrok.bat" "%INSTALL_DIR%\" >nul
copy "%SCRIPT_DIR%requirements.txt" "%INSTALL_DIR%\" >nul

REM Copy or create ngrok wrapper
if exist "%SCRIPT_DIR%ngrok.exe" (
    copy "%SCRIPT_DIR%ngrok.exe" "%INSTALL_DIR%\" >nul
) else (
    echo @echo off > "%INSTALL_DIR%\ngrok.bat"
    echo "%NGROK_CMD%" %%* >> "%INSTALL_DIR%\ngrok.bat"
)

echo [OK] Files installed

echo.
echo ============================================
echo [4/6] Installing Python libraries...
echo ============================================

"%PYTHON_CMD%" -m pip install --upgrade pip --quiet 2>nul
"%PYTHON_CMD%" -m pip install -r "%INSTALL_DIR%\requirements.txt" --quiet 2>nul

echo [OK] Libraries installed

echo.
echo ============================================
echo [5/6] Setting up auto-start...
echo ============================================

REM Get pythonw.exe path (same folder as python.exe)
for %%F in ("%PYTHON_CMD%") do set PYTHON_DIR=%%~dpF
SET "PYTHONW_CMD=%PYTHON_DIR%pythonw.exe"

REM Ngrok auto-start
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run """%INSTALL_DIR%\start_ngrok.bat""", 0, False
) > "%STARTUP_DIR%\RemoteWebcam_Ngrok.vbs"

REM Service auto-start
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run """%PYTHONW_CMD%"" ""%INSTALL_DIR%\main.py""", 0, False
) > "%STARTUP_DIR%\RemoteWebcam.vbs"

echo [OK] Auto-start configured

echo.
echo ============================================
echo [6/6] Starting services...
echo ============================================

start /B cmd /c ""%INSTALL_DIR%\start_ngrok.bat""
timeout /t 3 /nobreak >nul

start /B "%PYTHONW_CMD%" "%INSTALL_DIR%\main.py"
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo   INSTALLATION COMPLETE!
echo ============================================
echo.
echo Python: %PYTHON_CMD%
echo Ngrok:  %NGROK_CMD%
echo.
echo Service running in background (invisible)
echo Auto-starts on every boot
echo.
echo Cloud Server: https://connection-iyj0.onrender.com
echo Password: luohino
echo.
echo Open mobile app to see your device ONLINE!
echo.
echo ============================================
pause
