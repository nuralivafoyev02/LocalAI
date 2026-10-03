#!/bin/sh
set -eu

cd "$(dirname "$0")"

PYTHON=".venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    if ! command -v python3 >/dev/null 2>&1; then
        echo "Python 3 topilmadi. Avval Python 3 o'rnating." >&2
        exit 1
    fi
    python3 -m venv .venv
fi

if ! "$PYTHON" -c "import streamlit, pandas, openpyxl, xlrd, ollama, dotenv" >/dev/null 2>&1; then
    echo "Kerakli paketlar o'rnatilmoqda..."
    "$PYTHON" -m pip install -r requirements.txt
fi

PORT="${PORT:-8501}"
echo "LocalAI: http://127.0.0.1:${PORT}"
exec "$PYTHON" -m streamlit run app.py \
    --server.address 127.0.0.1 \
    --server.port "$PORT" \
    --server.maxUploadSize 25 \
    "$@"