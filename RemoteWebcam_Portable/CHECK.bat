@echo off
COLOR 0A
cls
echo ============================================
echo   SERVICE STATUS CHECK
echo ============================================
echo.

REM Check Python service
echo [1] Checking Python Service...
tasklist /FI "IMAGENAME eq pythonw.exe" 2>NUL | find /I /N "pythonw.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] Python service is RUNNING
) else (
    echo [X] Python service NOT running
)

echo.

REM Check ngrok
echo [2] Checking ngrok...
tasklist /FI "IMAGENAME eq ngrok.exe" 2>NUL | find /I /N "ngrok.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] ngrok is RUNNING
) else (
    echo [X] ngrok NOT running
)

echo.

REM Try to get ngrok URL
echo [3] Checking ngrok tunnel URL...
curl -s http://localhost:4040/api/tunnels > "%TEMP%\ngrok_check.json" 2>NUL
if %ERRORLEVEL%==0 (
    echo [OK] ngrok API responding
    echo.
    echo Tunnel URL:
    type "%TEMP%\ngrok_check.json" | findstr "public_url"
    del "%TEMP%\ngrok_check.json" 2>NUL
) else (
    echo [X] Cannot connect to ngrok API
)

echo.

REM Check signaling server
echo [4] Checking signaling server connection...
curl -s https://connection-iyj0.onrender.com > NUL 2>&1
if %ERRORLEVEL%==0 (
    echo [OK] Signaling server is reachable
    echo.
    echo Server status:
    curl -s https://connection-iyj0.onrender.com
) else (
    echo [X] Cannot reach signaling server
)

echo.

REM Check service logs
echo [5] Checking service logs...
if exist "C:\Program Files\RemoteWebcam\webcam_service.log" (
    echo [OK] Log file exists
    echo.
    echo Last 10 lines:
    powershell -Command "Get-Content 'C:\Program Files\RemoteWebcam\webcam_service.log' -Tail 10"
) else (
    echo [X] Log file not found
)

echo.
echo ============================================
echo   CHECK COMPLETE
echo ============================================
echo.
pause
