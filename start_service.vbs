Set WshShell = CreateObject("WScript.Shell")

' Run the backend silently
WshShell.Run "wsl ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000", 0, False

' Run the frontend silently 
WshShell.Run "cmd /c cd ..\TTS-Daneena && npm run dev", 0, False

' Wait 5 seconds and open the browser
WScript.Sleep 5000
WshShell.Run "http://localhost:3000"
