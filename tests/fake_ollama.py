"""Testlar va UI ishlab chiqish uchun Ollama API'ga o'xshash soxta server.

Ishga tushirish:  python tests/fake_ollama.py --port 11500
Keyin:           OLLAMA_BASE_URL=http://127.0.0.1:11500 python -m localai
"""

import argparse
import asyncio
import json
import re
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse


def create_fake(models=("qwen3.5:9b",), capabilities=("completion", "tools", "thinking"), delay=0.0):
    app = FastAPI()
    app.state.models = set(models)
    app.state.capabilities = list(capabilities)
    app.state.licenses = {}
    app.state.script = []
    app.state.requests = []
    app.state.created = []
    app.state.delay = delay

    def now():
        return datetime.now(timezone.utc).isoformat()

    @app.get("/api/tags")
    async def tags():
        return {"models": [{"name": name, "model": name} for name in sorted(app.state.models)]}

    @app.post("/api/show")
    async def show(request: Request):
        body = await request.json()
        name = body.get("model") or body.get("name")
        if name not in app.state.models and f"{name}:latest" not in app.state.models:
            return JSONResponse({"error": f"model '{name}' not found"}, status_code=404)
        return {
            "modelfile": "FROM test",
            "parameters": "",
            "template": "",
            "license": app.state.licenses.get(name, ""),
            "details": {"family": "qwen"},
            "model_info": {},
            "capabilities": app.state.capabilities,
            "modified_at": now(),
        }

    @app.post("/api/create")
    async def create(request: Request):
        body = await request.json()
        app.state.created.append(body)
        app.state.models.add(body["model"])
        license_value = body.get("license") or ""
        if isinstance(license_value, list):
            license_value = "\n".join(license_value)
        app.state.licenses[body["model"]] = license_value
        return {"status": "success"}

    def chunk(model, content="", thinking="", tool_calls=None, done=False):
        message = {"role": "assistant", "content": content}
        if thinking:
            message["thinking"] = thinking
        if tool_calls:
            message["tool_calls"] = tool_calls
        data = {"model": model, "created_at": now(), "message": message, "done": done}
        if done:
            data.update(done_reason="stop", eval_count=42, total_duration=1000)
        return json.dumps(data, ensure_ascii=False) + "\n"

    def demo_response(body):
        messages = body.get("messages", [])
        last = messages[-1] if messages else {"role": "user", "content": ""}
        tools = body.get("tools") or []
        thinking = "Foydalanuvchi savolini tahlil qilyapman. Eng foydali javobni tuzaman." if body.get("think") else ""
        if last.get("role") == "tool":
            lines = last.get("content", "").splitlines()
            preview = "\n".join(f"- `{line.strip()}`" for line in lines[1:7] if line.strip())
            return {
                "content": (
                    f"Natijani ko'rib chiqdim (`{last.get('tool_name')}`):\n\n{preview}\n\n"
                    "**Xulosa:** hammasi joyida, tahlil yakunlandi."
                ),
                "thinking": thinking,
            }
        text = re.sub(r"<guidelines>.*?</guidelines>", "", last.get("content", ""), flags=re.DOTALL)
        path = re.search(r"(~[^\s,]*|/[^\s,]+)", text)
        lowered = re.sub(r"(~[^\s,]*|/[^\s,]+)", " ", text).lower()
        if tools and ("papka" in lowered or "folder" in lowered) and path is not None:
            return {
                "content": "Papkani ko'rib chiqaman.",
                "thinking": thinking,
                "tool_calls": [{"function": {"name": "list_directory", "arguments": {"path": path.group(1), "depth": 1}}}],
            }
        if tools and ("o'qi" in lowered or "read" in lowered) and path is not None:
            return {"tool_calls": [{"function": {"name": "read_file", "arguments": {"path": path.group(1)}}}]}
        if tools and "hisobla" in lowered:
            expression = re.sub(r"[^0-9+\-*/(). ]", "", text).strip() or "2+2"
            return {"tool_calls": [{"function": {"name": "calculate", "arguments": {"expression": expression}}}]}
        if tools and "saqla" in lowered and path is not None:
            return {"tool_calls": [{"function": {"name": "write_file", "arguments": {
                "path": path.group(1), "content": "print('Salom, LocalAI!')\n"}}}]}
        return {
            "thinking": thinking,
            "content": (
                "## Javob\n\nBu **soxta** Ollama serveridan kelgan namunaviy javob. Unda ro'yxat, kod va jadval bor:\n\n"
                "1. Birinchi qadam — `pip install`\n2. Ikkinchi qadam\n   - ichki band\n\n"
                "```python\ndef salom(ism: str) -> str:\n    # Salomlashish\n    return f\"Salom, {ism}!\"\n\n"
                "print(salom(\"dunyo\"))\n```\n\n| Ustun | Qiymat |\n|---|---:|\n| A | 1 |\n| B | 2 |\n\n"
                "> Eslatma: bu faqat sinov uchun.\n"
            ),
        }

    @app.post("/api/chat")
    async def chat(request: Request):
        body = await request.json()
        app.state.requests.append(body)
        model = body.get("model")
        if model not in app.state.models:
            return JSONResponse({"error": f"model '{model}' not found"}, status_code=404)
        if body.get("tools") and "tools" not in app.state.capabilities:
            return JSONResponse({"error": f"registry.ollama.ai/library/{model} does not support tools"}, status_code=400)
        if body.get("think") and "thinking" not in app.state.capabilities:
            return JSONResponse({"error": f"\"{model}\" does not support thinking"}, status_code=400)
        response = app.state.script.pop(0) if app.state.script else demo_response(body)
        if response.get("error"):
            return JSONResponse({"error": response["error"]}, status_code=response.get("status", 500))

        async def stream():
            if response.get("thinking"):
                for word in re.findall(r"\S+\s*", response["thinking"]):
                    yield chunk(model, thinking=word)
                    await asyncio.sleep(app.state.delay)
            for piece in re.findall(r"\S+\s*|\s+", response.get("content", "")):
                yield chunk(model, content=piece)
                await asyncio.sleep(app.state.delay)
            if response.get("tool_calls"):
                yield chunk(model, tool_calls=response["tool_calls"])
            yield chunk(model, done=True)

        return StreamingResponse(stream(), media_type="application/x-ndjson")

    return app


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=11500)
    parser.add_argument("--delay", type=float, default=0.03)
    args = parser.parse_args()
    uvicorn.run(create_fake(delay=args.delay), host="127.0.0.1", port=args.port, log_level="warning")
