"""Ollama bilan aloqa: holat, model imkoniyatlari va `localai` modelini yaratish."""

import asyncio
import time

import httpx
import ollama

from .prompts import PERSONA, persona_fingerprint


def _names(payload):
    names = set()
    for item in payload.get("models", []):
        for key in ("name", "model"):
            if item.get(key):
                names.add(item[key])
    return names


def has_model(names, model):
    if model in names:
        return True
    if ":" not in model:
        return f"{model}:latest" in names
    return False


class ModelManager:
    """Qaysi model ishlatilishini aniqlaydi va kerak bo'lsa `localai` modelini yaratadi."""

    def __init__(self, settings, client_factory=None):
        self.settings = settings
        self.client_factory = client_factory or (
            lambda: ollama.AsyncClient(host=settings.ollama_base_url, timeout=settings.request_timeout)
        )
        self._lock = asyncio.Lock()
        self._status = None
        self._checked = 0.0
        self._capabilities = {}
        self._create_failed = None
        self._persona_verified = False

    def client(self):
        return self.client_factory()

    async def _tags(self):
        async with httpx.AsyncClient(timeout=4) as http:
            response = await http.get(self.settings.ollama_base_url + "/api/tags")
            response.raise_for_status()
            return response.json()

    async def capabilities(self, model):
        if model in self._capabilities:
            return self._capabilities[model]
        caps = None
        try:
            info = await self.client().show(model)
            raw = getattr(info, "capabilities", None)
            caps = set(raw) if raw else None
        except Exception:
            caps = None
        if caps is not None:
            self._capabilities[model] = caps
        return caps

    async def _model_is_current(self, client, name):
        try:
            info = await client.show(name)
        except Exception:
            return False
        license_text = getattr(info, "license", "") or ""
        modelfile = getattr(info, "modelfile", "") or ""
        marker = "localai-persona:" + persona_fingerprint()
        return marker in license_text or marker in modelfile

    async def ensure_persona_model(self, names):
        """`localai` modeli yo'q yoki eskirgan bo'lsa, asosiy modeldan yaratadi."""
        settings = self.settings
        if settings.model_name == settings.base_model or not has_model(names, settings.base_model):
            return has_model(names, settings.model_name)
        client = self.client()
        if has_model(names, settings.model_name):
            if self._persona_verified or await self._model_is_current(client, settings.model_name):
                self._persona_verified = True
                return True
        self._persona_verified = False
        try:
            await client.create(
                model=settings.model_name,
                from_=settings.base_model,
                system=PERSONA,
                license="localai-persona:" + persona_fingerprint(),
                parameters={"temperature": 0.7, "top_p": 0.8, "top_k": 20, "num_ctx": settings.num_ctx},
            )
            self._capabilities.pop(settings.model_name, None)
            self._create_failed = None
            self._persona_verified = True
            return True
        except Exception as error:
            self._create_failed = str(error)
            return has_model(names, settings.model_name)

    async def status(self, force=False):
        if not force and self._status and time.monotonic() - self._checked < 5:
            return self._status
        async with self._lock:
            if not force and self._status and time.monotonic() - self._checked < 5:
                return self._status
            self._status = await self._compute_status()
            self._checked = time.monotonic()
            return self._status

    async def _compute_status(self):
        settings = self.settings
        status = {
            "ollama": False,
            "ready": False,
            "model": None,
            "base_model": settings.base_model,
            "persona_model": settings.model_name,
            "capabilities": [],
            "message": "",
            "ollama_url": settings.ollama_base_url,
        }
        try:
            names = _names(await self._tags())
        except Exception:
            status["message"] = "Ollama bilan aloqa yo'q. Ollama ilovasini oching yoki `ollama serve` buyrug'ini ishga tushiring."
            return status
        status["ollama"] = True
        persona_ready = await self.ensure_persona_model(names)
        if persona_ready:
            model = settings.model_name
        elif has_model(names, settings.base_model):
            model = settings.base_model
        else:
            status["message"] = f"Model o'rnatilmagan. Terminalda: ollama pull {settings.base_model}"
            return status
        caps = await self.capabilities(model)
        status.update(
            ready=True,
            model=model,
            capabilities=sorted(caps) if caps else [],
            message="Tayyor" if model == settings.model_name else (
                "Asosiy model ishlatilmoqda" + (f" ({self._create_failed})" if self._create_failed else "")
            ),
        )
        return status

    def forget_capability(self, model, capability):
        caps = self._capabilities.get(model)
        if caps is not None:
            caps.discard(capability)
        else:
            self._capabilities[model] = {"completion"} | ({"tools", "thinking"} - {capability})
