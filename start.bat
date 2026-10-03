@echo off
rem LocalAI (Windows): start.bat
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual muhit yaratilmoqda...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo Python 3 topilmadi. https://www.python.org/downloads/ dan o'rnating.
        pause
        exit /b 1
    )
)
set "PYTHON=.venv\Scripts\python.exe"

"%PYTHON%" -c "import fastapi, uvicorn, httpx, ollama, pandas, openpyxl, xlrd, pypdf, docx, dotenv" 2>nul
if errorlevel 1 (
    echo Kerakli paketlar o'rnatilmoqda...
    "%PYTHON%" -m pip install -r requirements.txt
)

where ollama >nul 2>nul
if errorlevel 1 (
    echo Eslatma: Ollama topilmadi. https://ollama.com/download dan o'rnating.
) else (
    ollama list | findstr /b /c:"qwen3.5:9b" >nul || ollama pull qwen3.5:9b
)

"%PYTHON%" -m localai --open %*
pause
