#!/bin/sh
# LocalAI'ni ishga tushirish (macOS / Linux): ./start.sh
set -eu

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    if ! command -v python3 >/dev/null 2>&1; then
        echo "Python 3 topilmadi. Avval Python 3.10+ o'rnating: https://www.python.org/downloads/" >&2
        exit 1
    fi
    echo "Virtual muhit yaratilmoqda..."
    python3 -m venv .venv
fi
PYTHON=".venv/bin/python"

if ! "$PYTHON" -c "import fastapi, uvicorn, httpx, ollama, pandas, openpyxl, xlrd, pypdf, docx, dotenv" >/dev/null 2>&1; then
    echo "Kerakli paketlar o'rnatilmoqda..."
    "$PYTHON" -m pip install --upgrade pip >/dev/null
    "$PYTHON" -m pip install -r requirements.txt
fi

if command -v ollama >/dev/null 2>&1; then
    MODEL="${LOCALAI_BASE_MODEL:-qwen3.5:9b}"
    if ollama list >/dev/null 2>&1 && ! ollama list | awk '{print $1}' | grep -qx "$MODEL"; then
        echo "$MODEL modeli yuklab olinmoqda (bir marta, bir necha GB)..."
        ollama pull "$MODEL" || echo "Modelni yuklab bo'lmadi. Keyinroq: ollama pull $MODEL" >&2
    fi
else
    echo "Eslatma: Ollama topilmadi. https://ollama.com/download dan o'rnating." >&2
fi

exec "$PYTHON" -m localai --open "$@"
