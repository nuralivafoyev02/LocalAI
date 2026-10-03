"""Buyruqlar:

    python -m localai                # veb interfeysni ishga tushirish
    python -m localai create-model   # `localai` Ollama modelini yaratish/yangilash
    python -m localai modelfile      # Modelfile matnini chiqarish
    python -m localai doctor         # sozlamalarni tekshirish
"""

import argparse
import asyncio
import sys
import threading
import webbrowser

from . import __version__
from .config import Settings


def _print_status(status):
    mark = "✓" if status["ready"] else "✗"
    print(f"{mark} Ollama: {'ulangan' if status['ollama'] else 'ulanmagan'} ({status['ollama_url']})")
    if status["model"]:
        print(f"✓ Model: {status['model']}  (asosiy: {status['base_model']})")
        caps = ", ".join(status["capabilities"]) or "noma'lum"
        print(f"  Imkoniyatlar: {caps}")
    if status["message"] and status["message"] != "Tayyor":
        print(f"  {status['message']}")


def doctor(settings):
    from .models import ModelManager

    status = asyncio.run(ModelManager(settings).status(force=True))
    _print_status(status)
    print(f"  Ishchi papka: {settings.workspace}")
    print(f"  Ma'lumotlar papkasi: {settings.data_dir}")
    return 0 if status["ready"] else 1


def serve(settings, open_browser):
    import uvicorn

    from .server import create_app

    url = f"http://{'127.0.0.1' if settings.host in {'0.0.0.0', '::'} else settings.host}:{settings.port}"
    print(f"LocalAI {__version__}: {url}")
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, log_level="warning")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="localai", description="LocalAI — mahalliy AI yordamchi")
    parser.add_argument("command", nargs="?", default="serve", choices=["serve", "create-model", "modelfile", "doctor"])
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--open", action="store_true", help="brauzerni avtomatik ochish")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    if args.host:
        settings.host = args.host
    if args.port:
        settings.port = args.port

    if args.command == "modelfile":
        from .prompts import modelfile

        sys.stdout.write(modelfile(settings.base_model))
        return 0
    if args.command == "create-model":
        return doctor(settings)
    if args.command == "doctor":
        return doctor(settings)
    return serve(settings, args.open)


if __name__ == "__main__":
    sys.exit(main())
