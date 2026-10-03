"""Sozlamalar: hammasi muhit o'zgaruvchilari yoki .env fayli orqali boshqariladi."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _path(name, default):
    return Path(os.getenv(name) or default).expanduser().resolve()


@dataclass
class Settings:
    ollama_base_url: str = "http://localhost:11434"
    base_model: str = "qwen3.5:9b"
    model_name: str = "localai"
    num_ctx: int = 16384
    host: str = "127.0.0.1"
    port: int = 8501
    workspace: Path = field(default_factory=Path.home)
    data_dir: Path = field(default_factory=lambda: Path.home() / ".localai")
    max_upload_bytes: int = 25 * 1024 * 1024
    tool_output_chars: int = 12000
    max_tool_rounds: int = 10
    approval_timeout: int = 30 * 60
    request_timeout: int = 300
    extra_hosts: tuple = ()

    @property
    def upload_dir(self):
        return self.data_dir / "uploads"

    @classmethod
    def from_env(cls):
        extra_hosts = tuple(
            host.strip().lower()
            for host in os.getenv("LOCALAI_ALLOWED_HOSTS", "").split(",")
            if host.strip()
        )
        return cls(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
            base_model=os.getenv("LOCALAI_BASE_MODEL", "qwen3.5:9b").strip(),
            model_name=os.getenv("LOCALAI_MODEL", "localai").strip(),
            num_ctx=max(4096, _int("LOCALAI_NUM_CTX", 16384)),
            host=os.getenv("LOCALAI_HOST", "127.0.0.1"),
            port=_int("LOCALAI_PORT", _int("PORT", 8501)),
            workspace=_path("LOCALAI_WORKSPACE", Path.home()),
            data_dir=_path("LOCALAI_DATA_DIR", Path.home() / ".localai"),
            max_upload_bytes=max(1, _int("LOCALAI_MAX_UPLOAD_MB", 25)) * 1024 * 1024,
            extra_hosts=extra_hosts,
        )
