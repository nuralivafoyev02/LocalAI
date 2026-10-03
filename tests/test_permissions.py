from pathlib import Path

import pytest

from localai.permissions import GrantStore, PathError, display_path, is_sensitive, is_within, resolve_path


@pytest.mark.parametrize("path", [
    "/home/u/.ssh/id_rsa", "/home/u/project/.env", "/home/u/project/.env.local", "/x/server.pem",
    "/home/u/.aws/credentials", "/x/Cookies", "/x/secrets.json", "/x/id_ed25519.pub", "/x/vault.kdbx",
])
def test_sensitive_paths(path):
    assert is_sensitive(path)


@pytest.mark.parametrize("path", [
    "/home/u/project/main.py", "/home/u/.venv/lib/x.py", "/home/u/environment/notes.md", "/home/u/report.xlsx",
])
def test_regular_paths(path):
    assert not is_sensitive(path)


def test_is_within():
    assert is_within(Path("/a/b/c"), Path("/a/b"))
    assert is_within(Path("/a/b"), Path("/a/b"))
    assert not is_within(Path("/a/bc"), Path("/a/b"))


def test_resolve_relative_and_home(workspace):
    (workspace / "docs").mkdir()
    path, note = resolve_path("docs", workspace)
    assert path == (workspace / "docs").resolve() and note == ""
    path, _ = resolve_path("~/docs", workspace)
    assert path == (workspace / "docs").resolve()
    path, _ = resolve_path('"docs"', workspace)
    assert path == (workspace / "docs").resolve()
    path, _ = resolve_path("", workspace)
    assert path == workspace.resolve()


def test_resolve_corrects_typos(workspace):
    target = workspace / "Documents" / "Hisobotlar"
    target.mkdir(parents=True)
    (target / "yillik.txt").write_text("x")
    path, note = resolve_path("documnets/hisobotlar/yillik.txt", workspace)
    assert path == (target / "yillik.txt").resolve()
    assert "tuzatildi" in note


def test_resolve_uzbek_aliases(workspace):
    (workspace / "Desktop").mkdir()
    (workspace / "Downloads").mkdir()
    assert resolve_path("ish stoli", workspace)[0] == (workspace / "Desktop").resolve()
    assert resolve_path("Yuklanmalar", workspace)[0] == (workspace / "Downloads").resolve()
    assert resolve_path("dekstop", workspace)[0] == (workspace / "Desktop").resolve()


def test_resolve_missing_path_is_returned_unchanged(workspace):
    path, note = resolve_path("yoq/papka", workspace)
    assert path == (workspace / "yoq" / "papka").resolve()
    assert note == ""


def test_resolve_rejects_nul(workspace):
    with pytest.raises(PathError):
        resolve_path("a\x00b", workspace)


def test_display_path(workspace):
    assert display_path(workspace) == "~"
    assert display_path(workspace / "a") == "~/a"
    assert display_path("/etc/hosts") == "/etc/hosts"


def test_grant_store(tmp_path):
    grants = GrantStore()
    folder = tmp_path / "proj"
    grants.grant("chat", folder)
    assert grants.allows("chat", folder / "src" / "main.py")
    assert grants.allows("chat", folder)
    assert not grants.allows("chat", tmp_path / "other")
    assert not grants.allows("other-chat", folder / "a.py")
    assert not grants.allows("chat", folder / ".env")
    grants.revoke("chat")
    assert not grants.allows("chat", folder / "a.py")
