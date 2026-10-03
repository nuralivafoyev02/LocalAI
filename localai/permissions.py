"""Yo'llarni aniqlash, maxfiy fayllarni tanish va ruxsatlarni saqlash."""

import difflib
import os
import threading
from pathlib import Path


SENSITIVE_NAMES = {
    ".ssh", ".gnupg", ".gpg", ".aws", ".azure", ".gcloud", ".kube", ".docker",
    ".password-store", ".netrc", ".pgpass", ".npmrc", ".pypirc", ".git-credentials",
    ".vault-token", "keychains", "keyrings", "credentials", "credentials.json",
    "secrets", "secrets.json", "secrets.yaml", "secrets.yml", "login data", "cookies",
    "web data", "local state", "wallet.dat", "shadow", "gshadow", "sudoers",
}
SENSITIVE_PREFIXES = (".env", "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa")
SENSITIVE_SUFFIXES = {
    ".pem", ".key", ".p12", ".pfx", ".kdbx", ".keystore", ".jks", ".ovpn", ".gpg", ".asc",
}

# Foydalanuvchi papka nomini o'zbekcha, ruscha yoki xato bilan yozishi mumkin.
FOLDER_ALIASES = {
    "desktop": "Desktop", "dekstop": "Desktop", "destop": "Desktop", "ish stoli": "Desktop",
    "ishstoli": "Desktop", "рабочий стол": "Desktop",
    "documents": "Documents", "document": "Documents", "dokumentlar": "Documents",
    "hujjatlar": "Documents", "hujjat": "Documents", "документы": "Documents",
    "downloads": "Downloads", "download": "Downloads", "yuklanmalar": "Downloads",
    "yuklamalar": "Downloads", "yuklab olinganlar": "Downloads", "загрузки": "Downloads",
    "pictures": "Pictures", "rasmlar": "Pictures", "suratlar": "Pictures",
    "изображения": "Pictures", "music": "Music", "musiqa": "Music", "музыка": "Music",
    "videos": "Videos", "video": "Videos", "videolar": "Videos", "видео": "Videos",
}

QUOTES = "\"'`«»“”‘’"


class PathError(ValueError):
    pass


def is_sensitive(path):
    for part in Path(path).parts:
        lower = part.lower()
        if lower in SENSITIVE_NAMES or lower.startswith(SENSITIVE_PREFIXES):
            return True
    return Path(path).suffix.lower() in SENSITIVE_SUFFIXES


def is_within(path, folder):
    path, folder = Path(path), Path(folder)
    return path == folder or folder in path.parents


def _closest_child(parent, name):
    """Mavjud bo'lmagan nom uchun ota papkadagi eng yaqin nomni topadi."""
    try:
        children = [child.name for child in parent.iterdir()]
    except OSError:
        return None
    lower = name.lower()
    exact = [child for child in children if child.lower() == lower]
    if len(exact) == 1:
        return exact[0]
    alias = FOLDER_ALIASES.get(lower)
    if alias and alias in children:
        return alias
    if len(name) < 3:
        return None
    lowered = {child.lower(): child for child in children}
    matches = difflib.get_close_matches(lower, list(lowered), n=2, cutoff=0.8)
    if len(matches) == 1 or (
        len(matches) == 2
        and difflib.SequenceMatcher(None, lower, matches[0]).ratio()
        - difflib.SequenceMatcher(None, lower, matches[1]).ratio() > 0.08
    ):
        return lowered[matches[0]]
    return None


def resolve_path(raw, workspace):
    """Foydalanuvchi yoki model yozgan yo'lni haqiqiy yo'lga aylantiradi.

    Natija: (Path, izoh). Izoh yo'l taxminan tuzatilganda to'ldiriladi.
    """
    text = str(raw or "").strip().strip(QUOTES).strip()
    if not text or text in {".", "./"}:
        return Path(workspace).resolve(), ""
    if "\x00" in text:
        raise PathError("Yo'lda ruxsat etilmagan belgi bor.")
    text = os.path.expandvars(text)
    path = Path(text).expanduser()
    if not path.is_absolute():
        alias = FOLDER_ALIASES.get(text.lower().rstrip("/\\"))
        if alias:
            path = Path.home() / alias
        else:
            first = path.parts[0].lower() if path.parts else ""
            if first in FOLDER_ALIASES and not (Path(workspace) / path).exists():
                path = Path.home() / FOLDER_ALIASES[first] / Path(*path.parts[1:])
            else:
                path = Path(workspace) / path
    resolved = path.resolve()
    if resolved.exists():
        return resolved, ""

    # Xato yozilgan qismlarni bosqichma-bosqich tuzatishga urinib ko'ramiz.
    anchor = Path(resolved.anchor)
    current = anchor
    corrected = False
    for part in resolved.parts[1:]:
        candidate = current / part
        if candidate.exists():
            current = candidate
            continue
        match = _closest_child(current, part)
        if match is None:
            return resolved, ""
        current = current / match
        corrected = True
    if corrected:
        return current.resolve(), "Yo'l taxminan tuzatildi: " + str(current)
    return resolved, ""


def display_path(path):
    path = str(path)
    home = str(Path.home())
    if path == home:
        return "~"
    if path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path


class GrantStore:
    """Suhbat davomida ruxsat berilgan papkalar (server xotirasida saqlanadi)."""

    def __init__(self):
        self._grants = {}
        self._lock = threading.Lock()

    def grant(self, chat_id, folder):
        with self._lock:
            self._grants.setdefault(chat_id, set()).add(Path(folder))

    def allows(self, chat_id, path):
        if is_sensitive(path):
            return False
        with self._lock:
            folders = list(self._grants.get(chat_id, ()))
        return any(is_within(path, folder) for folder in folders)

    def folders(self, chat_id):
        with self._lock:
            return sorted(str(folder) for folder in self._grants.get(chat_id, ()))

    def revoke(self, chat_id):
        with self._lock:
            self._grants.pop(chat_id, None)
