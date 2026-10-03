import asyncio
from types import SimpleNamespace

import ollama
import pytest

from localai.agent import Agent, ApprovalBroker, ContentFilter, clean_history, fit_messages
from localai.permissions import GrantStore


def chunk(content="", thinking="", tool_calls=None, done=False):
    message = SimpleNamespace(content=content, thinking=thinking, tool_calls=tool_calls)
    return SimpleNamespace(message=message, done=done, eval_count=7 if done else None)


def call(name, **arguments):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=arguments))


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    async def chat(self, **kwargs):
        self.requests.append(kwargs)
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step

        async def stream():
            for item in step:
                yield item
            yield chunk(done=True)

        return stream()


class FakeManager:
    def __init__(self, client, caps=("completion", "tools", "thinking")):
        self._client = client
        self.caps = set(caps)

    async def status(self, force=False):
        return {"ready": True, "model": "localai", "message": "Tayyor"}

    async def capabilities(self, model):
        return self.caps

    def client(self):
        return self._client

    def forget_capability(self, model, capability):
        if self.caps is not None:
            self.caps.discard(capability)


async def collect(agent, broker, text, decisions=(), chat_id="c1", history=None, attachments=()):
    """Agentni ishga tushiradi va ruxsat so'rovlariga navbatma-navbat javob beradi."""
    decisions = list(decisions)
    events = []
    async for event in agent.run(chat_id, history or [], text, attachments):
        events.append(event)
        if event["type"] == "approval":
            decision = decisions.pop(0)
            asyncio.get_running_loop().call_soon(broker.resolve, event["id"], decision)
    return events


def make_agent(settings, script, caps=("completion", "tools", "thinking")):
    client = FakeClient(script)
    broker = ApprovalBroker()
    grants = GrantStore()
    agent = Agent(settings, FakeManager(client, caps), grants, broker)
    return agent, broker, grants, client


def text_of(events):
    return "".join(event["delta"] for event in events if event["type"] == "token")


def test_simple_answer_streams_tokens(settings):
    agent, broker, _, client = make_agent(settings, [[chunk("Salom"), chunk(", dunyo!")]])
    events = asyncio.run(collect(agent, broker, "salom"))
    assert text_of(events) == "Salom, dunyo!"
    assert events[0]["type"] == "meta" and events[-1]["type"] == "done"
    messages = [event["message"] for event in events if event["type"] == "message"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    request = client.requests[0]
    assert request["messages"][0]["role"] == "system" and "LocalAI" in request["messages"][0]["content"]
    assert request["think"] is False and request["tools"]


def test_tool_call_with_approval(settings, workspace):
    (workspace / "proj").mkdir()
    (workspace / "proj" / "a.txt").write_text("ichki matn")
    script = [
        [chunk("Ko'rib chiqaman."), chunk(tool_calls=[call("read_file", path="proj/a.txt")])],
        [chunk("Faylda «ichki matn» yozilgan.")],
    ]
    agent, broker, _, client = make_agent(settings, script)
    events = asyncio.run(collect(agent, broker, "a.txt ni o'qi", ["allow"]))
    kinds = [event["type"] for event in events]
    assert kinds.index("tool") < kinds.index("approval") < kinds.index("approval_done") < kinds.index("tool_done")
    done = next(event for event in events if event["type"] == "tool_done")
    assert done["status"] == "done"
    tool_message = client.requests[1]["messages"][-1]
    assert tool_message["role"] == "tool" and "ichki matn" in tool_message["content"]
    assert "ichki matn" in text_of(events)


def test_denied_tool_is_reported_to_model(settings, workspace):
    (workspace / "s.txt").write_text("maxfiy")
    script = [[chunk(tool_calls=[call("read_file", path="s.txt")])], [chunk("Mayli, o'qimayman.")]]
    agent, broker, _, client = make_agent(settings, script)
    events = asyncio.run(collect(agent, broker, "o'qi", ["deny"]))
    assert next(e for e in events if e["type"] == "tool_done")["status"] == "denied"
    assert "ruxsat bermadi" in client.requests[1]["messages"][-1]["content"]
    assert "maxfiy" not in str(client.requests[1]["messages"])


def test_folder_grant_skips_next_approval(settings, workspace):
    folder = workspace / "proj"
    folder.mkdir()
    (folder / "a.txt").write_text("A")
    (folder / "b.txt").write_text("B")
    script = [
        [chunk(tool_calls=[call("list_directory", path="proj")])],
        [chunk(tool_calls=[call("read_file", path="proj/a.txt"), call("read_file", path="proj/b.txt")])],
        [chunk("Tayyor")],
    ]
    agent, broker, grants, _ = make_agent(settings, script)
    events = asyncio.run(collect(agent, broker, "loyihani ko'r", ["allow_folder"]))
    assert sum(1 for event in events if event["type"] == "approval") == 1
    assert [e["status"] for e in events if e["type"] == "tool_done"] == ["done", "done", "done"]
    assert grants.allows("c1", folder / "a.txt")


def test_write_always_needs_approval_even_with_grant(settings, workspace):
    script = [[chunk(tool_calls=[call("write_file", path="out.txt", content="salom")])], [chunk("Saqlandi.")]]
    agent, broker, grants, _ = make_agent(settings, script)
    grants.grant("c1", workspace)
    events = asyncio.run(collect(agent, broker, "saqla", ["allow"]))
    approval = next(e for e in events if e["type"] == "approval")
    assert approval["access"] == "write" and approval["preview"] == "salom" and approval["folder"] is None
    assert (workspace / "out.txt").read_text() == "salom"


def test_text_tool_call_fallback_and_think_tags(settings):
    script = [
        [chunk("<thi"), chunk("nk>reja tuzaman</think>Hisoblayman <tool"), chunk('_call>{"name": "calculate", '),
         chunk('"arguments": {"expression": "6*7"}}</tool_call>')],
        [chunk("Javob: **42**")],
    ]
    agent, broker, _, client = make_agent(settings, script)
    events = asyncio.run(collect(agent, broker, "6*7 hisobla"))
    assert "<tool_call>" not in text_of(events) and "<think>" not in text_of(events)
    assert "".join(e["delta"] for e in events if e["type"] == "thinking") == "reja tuzaman"
    assert "6*7 = 42" in client.requests[1]["messages"][-1]["content"]
    assert text_of(events).endswith("Javob: **42**")


def test_tools_unsupported_falls_back(settings):
    error = ollama.ResponseError("registry.ollama.ai/library/x does not support tools", 400)
    agent, broker, _, client = make_agent(settings, [error, [chunk("Oddiy javob")]], caps=())
    agent.manager.caps = None

    async def no_caps(model):
        return None

    agent.manager.capabilities = no_caps
    events = asyncio.run(collect(agent, broker, "salom"))
    assert text_of(events) == "Oddiy javob"
    assert client.requests[1]["tools"] is None


def test_unknown_tool_and_duplicate_calls(settings):
    script = [
        [chunk(tool_calls=[call("hack_the_planet"), call("calculate", expression="1+1"),
                           call("calculate", expression="1+1")])],
        [chunk("ok")],
    ]
    agent, broker, _, client = make_agent(settings, script)
    asyncio.run(collect(agent, broker, "x"))
    tool_messages = [m for m in client.requests[1]["messages"] if m["role"] == "tool"]
    assert "yo'q" in tool_messages[0]["content"]
    assert tool_messages[1]["content"] == "1+1 = 2"
    assert "allaqachon" in tool_messages[2]["content"]


def test_connection_error_is_friendly(settings):
    import httpx

    agent, broker, _, _ = make_agent(settings, [httpx.ConnectError("refused")])
    events = asyncio.run(collect(agent, broker, "salom"))
    assert events[-1]["type"] == "error" and "Ollama" in events[-1]["message"]


def test_tool_round_limit(settings):
    settings.max_tool_rounds = 2
    script = [
        [chunk(tool_calls=[call("calculate", expression="1+1")])],
        [chunk(tool_calls=[call("calculate", expression="2+2")])],
        [chunk("Yakuniy javob")],
    ]
    agent, broker, _, client = make_agent(settings, script)
    events = asyncio.run(collect(agent, broker, "x"))
    assert client.requests[2]["tools"] is None
    assert text_of(events) == "Yakuniy javob"


def test_attachments_are_injected(settings, workspace):
    upload = settings.upload_dir / "abcdefgh" / "eslatma.txt"
    upload.parent.mkdir(parents=True)
    upload.write_text("Ertaga soat 9 da yig'ilish")
    agent, broker, _, client = make_agent(settings, [[chunk("Tushunarli")]])
    attachments = [{"id": "abcdefgh", "name": "eslatma.txt", "path": str(upload)}]
    asyncio.run(collect(agent, broker, "", attachments=attachments))
    user = client.requests[0]["messages"][-1]["content"]
    assert "Ertaga soat 9 da" in user and '<file name="eslatma.txt"' in user
    assert "Biriktirilgan faylni" in user


def test_thinking_enabled_when_requested(settings):
    agent, broker, _, client = make_agent(settings, [[chunk(thinking="o'ylayapman"), chunk("Javob")]])

    async def run():
        return [event async for event in agent.run("c", [], "qiyin savol", (), think=True)]

    events = asyncio.run(run())
    assert client.requests[0]["think"] is True
    assert any(event["type"] == "thinking" for event in events)


def test_content_filter_handles_split_tags():
    content_filter = ContentFilter()
    out = []
    for piece in ["Salom <", "th", "ink>ichki", "</thi", "nk> dunyo <b>qalin</b>"]:
        out.extend(content_filter.feed(piece))
    out.extend(content_filter.flush())
    text = "".join(part for kind, part in out if kind == "text")
    thinking = "".join(part for kind, part in out if kind == "thinking")
    assert text == "Salom  dunyo <b>qalin</b>" and thinking == "ichki"


def test_clean_history_drops_invalid_entries():
    history = [
        {"role": "tool", "content": "orphan"},
        {"role": "system", "content": "hack"},
        {"role": "user", "content": "salom"},
        {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "calculate", "arguments": {"expression": "1"}}}]},
        {"role": "tool", "content": "1 = 1", "tool_name": "calculate"},
        "not a dict",
    ]
    cleaned = clean_history(history)
    assert [m["role"] for m in cleaned] == ["user", "assistant", "tool"]


def test_fit_messages_respects_budget(settings):
    settings.num_ctx = 4096
    history = []
    for index in range(40):
        history.append({"role": "user", "content": f"savol {index} " + "x" * 800})
        history.append({"role": "assistant", "content": f"javob {index} " + "y" * 800})
    current = [{"role": "user", "content": "oxirgi savol"}]
    messages = fit_messages("tizim", history, current, settings)
    assert messages[0]["role"] == "system" and messages[-1]["content"] == "oxirgi savol"
    total = sum(len(m["content"]) for m in messages)
    assert total < settings.num_ctx * 2.8
    assert "javob 39" in messages[-2]["content"]
    assert len(messages) < 40


def test_broker_resolve_unknown():
    async def run():
        broker = ApprovalBroker()
        approval_id, future = broker.create()
        assert broker.resolve(approval_id, "allow")
        assert not broker.resolve(approval_id, "deny")
        assert not broker.resolve("nope", "allow")
        return await future

    assert asyncio.run(run()) == "allow"


@pytest.mark.parametrize("model_message", ["", "   "])
def test_empty_model_answer_reports_error(settings, model_message):
    agent, broker, _, _ = make_agent(settings, [[chunk(model_message)]])
    events = asyncio.run(collect(agent, broker, "salom"))
    assert any(event["type"] == "error" for event in events)


def test_fit_messages_shortens_huge_user_message(settings):
    settings.num_ctx = 4096
    huge = "BOSHI " + "z" * 50000 + " OXIRI"
    messages = fit_messages("tizim", [], [{"role": "user", "content": huge}], settings)
    content = messages[-1]["content"]
    assert content.startswith("BOSHI") and content.endswith("OXIRI")
    assert len(content) < settings.num_ctx * 2.8 and "tushirib qoldirildi" in content


def test_guidelines_only_in_model_copy(settings):
    agent, broker, _, client = make_agent(settings, [[chunk("ok")]])
    events = asyncio.run(collect(agent, broker, "/kod python funksiya"))
    sent = client.requests[0]["messages"][-1]["content"]
    stored = next(e["message"] for e in events if e["type"] == "message")
    assert "<guidelines>" in sent and "Skill: Coding" in sent
    assert "<guidelines>" not in stored["content"] and stored["content"] == "python funksiya"
    assert "Skill: Coding" not in client.requests[0]["messages"][0]["content"]
