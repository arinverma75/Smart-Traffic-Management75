@echo off
cd /d "%~dp0"
rem Load variables from .env if it exists
if exist .env (
    for /f "usebackq tokens=1* delims==" %%A in (".env") do (
        set "%%A=%%B"
    )
)
rem Optionally set GOOGLE_MAPS_API_KEY before starting to enable real Google map tiles
rem   set GOOGLE_MAPS_API_KEY=your_key_here

 echo Starting Smart Traffic Management on http://localhost:8000
echo Open this URL in your browser. Press CTRL+C to stop the server.
echo.
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port %PORT:8000%
    echo Server exited with an error. Press any key to close.
    pause >nul
)
