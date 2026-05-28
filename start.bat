@echo off
echo Starting EA-TTS...

:: Start the frontend in a separate command window
start "EA-TTS Frontend" cmd /c "cd ..\TTS-Daneena && npm run dev"

:: Wait a few seconds to let the servers spin up, then open the browser
timeout /t 5 /nobreak >nul
start http://localhost:3000

:: Start the backend in the current window
echo Starting EA-TTS Backend inside WSL (Ubuntu/Linux)...
wsl env WATCHFILES_FORCE_POLLING=true ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
