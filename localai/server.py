"""HTTP server: veb interfeys, oqimli chat, ruxsatlar va fayl yuklash."""

import asyncio
import json
import re
import secrets
import shutil
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .agent import Agent, ApprovalBroker
from .config import Settings
from .files import human_size
from .models import ModelManager
from .permissions import GrantStore, display_path
from .skills import public_skills


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
UPLOAD_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
UPLOAD_TTL = 7 * 24 * 3600


class ChatRequest(BaseModel):
    chat_id: str = Field(min_length=1, max_length=100)
    message: str = Field(default="", max_length=300_000)
    history: list = Field(default_factory=list, max_length=2000)
    attachments: list[str] = Field(default_factory=list, max_length=10)
    think: bool = False


class ApprovalRequest(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    decision: str = Field(pattern="^(allow|allow_folder|deny)$")


class ForgetRequest(BaseModel):
    chat_id: str = Field(min_length=1, max_length=100)


def safe_filename(name):
    name = Path(str(name or "fayl").replace("\\", "/")).name
    name = re.sub(r"[\x00-\x1f<>:\"/\\|?*]", "_", name).strip(" .") or "fayl"
    return name[:150]


def clean_old_uploads(upload_dir, ttl=UPLOAD_TTL):
    if not upload_dir.exists():
        return
    cutoff = time.time() - ttl
    for folder in upload_dir.iterdir():
        try:
            if folder.is_dir() and folder.stat().st_mtime < cutoff:
                shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            continue


def find_upload(settings, upload_id):
    if not UPLOAD_ID.match(upload_id or ""):
        return None
    folder = settings.upload_dir / upload_id
    if not folder.is_dir():
        return None
    for item in folder.iterdir():
        if item.is_file():
            return item.resolve()
    return None


def create_app(settings=None, manager=None):
    settings = settings or Settings.from_env()
    manager = manager or ModelManager(settings)
    grants = GrantStore()
    broker = ApprovalBroker()
    agent = Agent(settings, manager, grants, broker)
    allowed_hosts = set(LOCAL_HOSTS) | set(settings.extra_hosts)
    if settings.host not in {"0.0.0.0", "::", ""}:
        allowed_hosts.add(settings.host.lower())
    allow_any_host = "*" in allowed_hosts

    @asynccontextmanager
    async def lifespan(app):
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(clean_old_uploads, settings.upload_dir)
        warmup = asyncio.create_task(manager.status(force=True))
        yield
        warmup.cancel()

    app = FastAPI(title="LocalAI", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.manager = manager
    app.state.grants = grants
    app.state.broker = broker

    @app.middleware("http")
    async def guard(request: Request, call_next):
        # DNS-rebinding va boshqa saytlardan keladigan so'rovlardan himoya.
        host = urlsplit("//" + request.headers.get("host", "")).hostname or ""
        if not allow_any_host and host.lower() not in allowed_hosts:
            return PlainTextResponse("Ruxsat etilmagan host", status_code=403)
        if request.url.path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and not allow_any_host:
                origin_host = (urlsplit(origin).hostname or "").lower()
                if origin_host not in allowed_hosts:
                    return PlainTextResponse("Ruxsat etilmagan manba", status_code=403)
            content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
            if request.method == "POST" and content_type not in {"application/json", "application/octet-stream"}:
                return PlainTextResponse("Noto'g'ri Content-Type", status_code=415)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    @app.get("/", response_class=HTMLResponse)
    async def index():
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8").replace("{{VERSION}}", __version__)
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-cache",
                "Content-Security-Policy": (
                    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                    "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
                ),
            },
        )

    @app.get("/favicon.ico")
    async def favicon():
        return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/api/status")
    async def status(refresh: bool = False):
        data = dict(await manager.status(force=refresh))
        host = urlsplit(settings.ollama_base_url).hostname or ""
        data.update(
            version=__version__,
            workspace=display_path(settings.workspace),
            private=host in LOCAL_HOSTS,
            max_upload=settings.max_upload_bytes,
        )
        return data

    @app.get("/api/skills")
    async def skills():
        return {"skills": public_skills()}

    @app.post("/api/chat")
    async def chat(payload: ChatRequest):
        attachments = []
        for upload_id in payload.attachments:
            path = find_upload(settings, upload_id)
            if path is not None:
                attachments.append({"id": upload_id, "name": path.name, "path": str(path)})

        async def stream():
            try:
                async for event in agent.run(
                    payload.chat_id, payload.history, payload.message, attachments, payload.think,
                ):
                    yield json.dumps(event, ensure_ascii=False, default=str) + "\n"
            except asyncio.CancelledError:
                raise
            except Exception as error:
                yield json.dumps({"type": "error", "message": f"Server xatosi: {error}"}, ensure_ascii=False) + "\n"

        return StreamingResponse(
            stream(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/approve")
    async def approve(payload: ApprovalRequest):
        if not broker.resolve(payload.id, payload.decision):
            return JSONResponse({"ok": False, "error": "So'rov topilmadi yoki muddati o'tgan"}, status_code=404)
        return {"ok": True}

    @app.post("/api/forget")
    async def forget(payload: ForgetRequest):
        grants.revoke(payload.chat_id)
        return {"ok": True}

    @app.post("/api/upload")
    async def upload(request: Request, name: str = "fayl"):
        filename = safe_filename(name)
        upload_id = secrets.token_urlsafe(12)
        folder = settings.upload_dir / upload_id
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / filename
        size = 0
        try:
            with open(target, "wb") as handle:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise ValueError("too-large")
                    handle.write(chunk)
        except ValueError:
            shutil.rmtree(folder, ignore_errors=True)
            limit = human_size(settings.max_upload_bytes)
            return JSONResponse({"ok": False, "error": f"Fayl {limit} limitdan katta."}, status_code=413)
        except Exception as error:
            shutil.rmtree(folder, ignore_errors=True)
            return JSONResponse({"ok": False, "error": f"Faylni saqlab bo'lmadi: {error}"}, status_code=500)
        if size == 0:
            shutil.rmtree(folder, ignore_errors=True)
            return JSONResponse({"ok": False, "error": "Fayl bo'sh."}, status_code=400)
        return {"ok": True, "id": upload_id, "name": filename, "size": size}

    @app.delete("/api/upload/{upload_id}")
    async def delete_upload(upload_id: str):
        if UPLOAD_ID.match(upload_id):
            shutil.rmtree(settings.upload_dir / upload_id, ignore_errors=True)
        return {"ok": True}

    return app
