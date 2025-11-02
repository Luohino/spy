@echo off
COLOR 0A
cls
echo ============================================
echo   REMOTE WEBCAM - ONE-CLICK INSTALLER
echo ============================================
echo.
echo This will automatically install:
echo  [1] Python 3.11 (if not installed)
echo  [2] Ngrok (included)
echo  [3] All required libraries
echo  [4] Auto-start on boot
echo  [5] Connect to cloud server
echo.
echo Works on BRAND NEW Windows 11!
echo No manual setup required!
echo.
pause

REM ============================================
REM Check for Administrator privileges
REM ============================================
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ============================================
    echo   ADMINISTRATOR RIGHTS REQUIRED!
    echo ============================================
    echo.
    echo Please right-click this file and select
    echo "Run as Administrator"
    echo.
    pause
    exit /b 1
)

REM ============================================
REM Set Paths
REM ============================================
SET SCRIPT_DIR=%~dp0
SET INSTALL_DIR=%ProgramFiles%\RemoteWebcam
SET PYTHON_INSTALLER=%SCRIPT_DIR%python-installer.exe
SET NGROK_EXE=%SCRIPT_DIR%ngrok.exe
SET STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

echo.
echo ============================================
echo [1/6] Checking Python Installation...
echo ============================================

REM Check if Python is already installed
python --version >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] Python is already installed
    python --version
) else (
    echo [!] Python not found. Installing Python 3.11...
    
    REM Check if Python installer exists
    if exist "%PYTHON_INSTALLER%" (
        echo Installing from: %PYTHON_INSTALLER%
        start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        
        REM Refresh PATH
        call refreshenv >nul 2>&1
        
        echo [OK] Python installed successfully!
    ) else (
        echo.
        echo ============================================
        echo   PYTHON INSTALLER NOT FOUND!
        echo ============================================
        echo.
        echo Please download Python 3.11 installer:
        echo https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
        echo.
        echo Save it as: %PYTHON_INSTALLER%
        echo Then run this installer again.
        echo.
        echo OR: Install Python manually, then run again.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ============================================
echo [2/6] Setting up Ngrok...
echo ============================================

REM Check if ngrok.exe exists in portable folder
if exist "%NGROK_EXE%" (
    echo [OK] Found ngrok.exe in portable folder
) else (
    echo.
    echo ============================================
    echo   NGROK NOT FOUND!
    echo ============================================
    echo.
    echo Please download ngrok:
    echo https://ngrok.com/download
    echo.
    echo Save ngrok.exe to: %SCRIPT_DIR%
    echo Then run this installer again.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo [3/6] Creating installation directory...
echo ============================================

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy all files
copy "%SCRIPT_DIR%main.py" "%INSTALL_DIR%\" >nul
copy "%SCRIPT_DIR%ngrok_helper.py" "%INSTALL_DIR%\" >nul
copy "%SCRIPT_DIR%start_ngrok.bat" "%INSTALL_DIR%\" >nul
copy "%NGROK_EXE%" "%INSTALL_DIR%\" >nul
copy "%SCRIPT_DIR%requirements.txt" "%INSTALL_DIR%\" >nul

echo [OK] Files copied to %INSTALL_DIR%

echo.
echo ============================================
echo [4/6] Installing Python dependencies...
echo ============================================

REM Upgrade pip first
python -m pip install --upgrade pip --quiet

REM Install requirements
if exist "%INSTALL_DIR%\requirements.txt" (
    echo Installing required libraries...
    python -m pip install -r "%INSTALL_DIR%\requirements.txt" --quiet
    echo [OK] All dependencies installed!
) else (
    echo [!] requirements.txt not found, installing manually...
    python -m pip install flask flask-cors flask-socketio opencv-python requests python-socketio websocket-client numpy --quiet
    echo [OK] Dependencies installed!
)

echo.
echo ============================================
echo [5/6] Setting up auto-start on boot...
echo ============================================

REM Create VBScript for ngrok auto-start
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run """%INSTALL_DIR%\start_ngrok.bat""", 0, False
) > "%STARTUP_DIR%\RemoteWebcam_Ngrok.vbs"

REM Create VBScript for service auto-start
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run "pythonw ""%INSTALL_DIR%\main.py""", 0, False
) > "%STARTUP_DIR%\RemoteWebcam.vbs"

echo [OK] Auto-start configured!

echo.
echo ============================================
echo [6/6] Starting services...
echo ============================================

REM Start ngrok
echo Starting ngrok tunnel...
start /B cmd /c ""%INSTALL_DIR%\start_ngrok.bat""
timeout /t 3 /nobreak >nul

REM Start service
echo Starting webcam service...
start /B pythonw "%INSTALL_DIR%\main.py"
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo   INSTALLATION COMPLETE!
echo ============================================
echo.
echo [*] Service is running in background
echo [*] Will auto-start on every boot
echo [*] Connected to cloud server
echo.
echo Cloud Server: https://connection-iyj0.onrender.com
echo Password: luohino
echo.
echo TO USE FROM MOBILE:
echo ------------------
echo 1. Install mobile app on your phone
echo 2. Open app (auto-connects to server)
echo 3. Your device will appear as ONLINE
echo 4. Tap to view webcam
echo.
echo Works from ANYWHERE in the world!
echo No port forwarding needed!
echo.
echo ============================================
pause
