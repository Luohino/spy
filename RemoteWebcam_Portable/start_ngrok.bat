@echo off
REM Start ngrok tunnel for port 5000 and save URL to file

REM Kill any existing ngrok processes
taskkill /F /IM ngrok.exe >nul 2>&1

REM Start ngrok in background
start /B ngrok http 5000 --log=stdout > ngrok.log 2>&1

REM Wait for ngrok to start
timeout /t 5 /nobreak >nul

REM Get ngrok URL from API
powershell -Command "try { $response = Invoke-RestMethod -Uri 'http://localhost:4040/api/tunnels' -ErrorAction Stop; $url = $response.tunnels[0].public_url; $url | Out-File -FilePath 'ngrok_url.txt' -Encoding ASCII -NoNewline; Write-Host 'Ngrok URL:' $url } catch { Write-Host 'Waiting for ngrok...' }"

exit
