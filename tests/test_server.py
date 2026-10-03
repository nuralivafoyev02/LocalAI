import json
from pathlib import Path

import httpx
import pytest

from conftest import ServerThread
from fake_ollama import create_fake
from localai.prompts import modelfile, persona_fingerprint
from localai.server import create_app


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def stack(settings):
    fake = create_fake()
    with ServerThread(fake) as ollama_server:
        settings.ollama_base_url = ollama_server.url
        app = create_app(settings)
        with ServerThread(app) as app_server:
            yield fake, app_server, settings


def stream_chat(base, payload, decisions=()):
    decisions = list(decisions)
    events = []
    with httpx.Client(base_url=base, timeout=30) as client:
        with client.stream("POST", "/api/chat", json=payload) as response:
            assert response.status_code == 200
            for line in response.iter_lines():
                if not line:
                    continue
                event = json.loads(line)
                events.append(event)
                if event["type"] == "approval":
                    reply = httpx.post(base + "/api/approve", json={"id": event["id"], "decision": decisions.pop(0)})
                    assert reply.status_code == 200
    return events


def test_status_creates_persona_model(stack):
    fake, server, settings = stack
    status = httpx.get(server.url + "/api/status").json()
    assert status["ready"] and status["model"] == "localai"
    assert "tools" in status["capabilities"]
    created = fake.state.created[0]
    assert created["model"] == "localai" and created["from"] == "qwen3.5:9b"
    assert persona_fingerprint() in str(created["license"])
    httpx.get(server.url + "/api/status?refresh=1")
    assert len(fake.state.created) == 1  # Model yangi bo'lsa, qayta yaratilmaydi.


def test_status_when_base_model_missing(settings):
    fake = create_fake(models=())
    with ServerThread(fake) as ollama_server:
        settings.ollama_base_url = ollama_server.url
        with ServerThread(create_app(settings)) as server:
            status = httpx.get(server.url + "/api/status").json()
    assert not status["ready"] and "ollama pull" in status["message"]


def test_status_when_ollama_offline(settings):
    settings.ollama_base_url = "http://127.0.0.1:9"
    with ServerThread(create_app(settings)) as server:
        status = httpx.get(server.url + "/api/status").json()
        events = stream_chat(server.url, {"chat_id": "x", "message": "salom"})
    assert not status["ollama"] and "aloqa" in status["message"]
    assert events[-1]["type"] == "error"


def test_chat_with_folder_approval(stack, workspace):
    fake, server, _ = stack
    folder = workspace / "loyiha"
    folder.mkdir()
    (folder / "main.py").write_text("print(1)\n")
    events = stream_chat(server.url, {"chat_id": "c", "message": f"{folder} papkasini ko'r"}, ["allow_folder"])
    kinds = [event["type"] for event in events]
    assert "approval" in kinds and kinds[-1] == "done"
    assert next(e for e in events if e["type"] == "tool_done")["status"] == "done"
    history = [event["message"] for event in events if event["type"] == "message"]
    events = stream_chat(server.url, {"chat_id": "c", "message": f"{folder}/main.py ni o'qi", "history": history})
    assert "approval" not in [event["type"] for event in events]
    last_request = fake.state.requests[-1]
    assert any("print(1)" in message.get("content", "") for message in last_request["messages"])


def test_upload_and_attachment(stack):
    fake, server, settings = stack
    response = httpx.post(
        server.url + "/api/upload?name=../../hisobot.csv",
        content=b"ism,yosh\nAli,25\nVali,30\n",
        headers={"Content-Type": "application/octet-stream"},
    )
    data = response.json()
    assert data["ok"] and data["name"] == "hisobot.csv"
    stored = settings.upload_dir / data["id"] / "hisobot.csv"
    assert stored.exists()
    stream_chat(server.url, {"chat_id": "u", "message": "tahlil qil", "attachments": [data["id"], "../bad"]})
    user = fake.state.requests[-1]["messages"][-1]["content"]
    assert "Vali" in user and "hisobot.csv" in user
    assert httpx.delete(server.url + f"/api/upload/{data['id']}").json()["ok"]
    assert not stored.exists()


def test_upload_limits(stack):
    _, server, settings = stack
    settings.max_upload_bytes = 10
    response = httpx.post(server.url + "/api/upload?name=a.txt", content=b"x" * 50,
                          headers={"Content-Type": "application/octet-stream"})
    assert response.status_code == 413
    response = httpx.post(server.url + "/api/upload?name=a.txt", content=b"",
                          headers={"Content-Type": "application/octet-stream"})
    assert response.status_code == 400


def test_security_guards(stack):
    _, server, _ = stack
    assert httpx.get(server.url + "/api/status", headers={"Host": "evil.example"}).status_code == 403
    response = httpx.post(server.url + "/api/chat", json={"chat_id": "x", "message": "hi"},
                          headers={"Origin": "http://evil.example"})
    assert response.status_code == 403
    response = httpx.post(server.url + "/api/chat", content='{"chat_id": "x"}', headers={"Content-Type": "text/plain"})
    assert response.status_code == 415
    assert httpx.post(server.url + "/api/approve", json={"id": "nope", "decision": "allow"}).status_code == 404
    assert httpx.post(server.url + "/api/approve", json={"id": "x", "decision": "maybe"}).status_code == 422


def test_index_and_static(stack):
    _, server, _ = stack
    page = httpx.get(server.url + "/")
    assert page.status_code == 200 and "LocalAI" in page.text and "{{VERSION}}" not in page.text
    assert "script-src 'self'" in page.headers["content-security-policy"]
    for asset in ("app.js", "markdown.js", "styles.css", "favicon.svg"):
        assert httpx.get(server.url + "/static/" + asset).status_code == 200
    skills = httpx.get(server.url + "/api/skills").json()["skills"]
    assert {skill["command"] for skill in skills} >= {"/kod", "/imlo", "/tahlil", "/papka"}


def test_modelfile_in_repo_is_up_to_date():
    assert (ROOT / "Modelfile").read_text(encoding="utf-8") == modelfile("qwen3.5:9b")
