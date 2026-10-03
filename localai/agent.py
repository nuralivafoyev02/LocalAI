"""Agent sikli: model javobini oqim bilan uzatadi, vositalarni ruxsat asosida bajaradi."""

import asyncio
import json
import re
import secrets
import time

import httpx
import ollama

from . import files
from .permissions import display_path
from .prompts import request_guidelines, system_prompt
from .skills import normalize_text, select_skills
from .tools import (
    ToolContext, ToolError, find_tool, needs_approval, target_label, time_text, today_text, tool_schemas,
)


HISTORY_TOOL_CHARS = 6000
ATTACHMENT_CHARS = 12000
ATTACHMENTS_TOTAL_CHARS = 24000
CHARS_PER_TOKEN = 2.8
TOOL_SCHEMA_CHARS = len(json.dumps(tool_schemas(), ensure_ascii=False))


class ApprovalBroker:
    """Foydalanuvchi qaroriga muhtoj so'rovlarni kutib turadi."""

    def __init__(self):
        self._pending = {}

    def create(self):
        approval_id = secrets.token_urlsafe(12)
        future = asyncio.get_running_loop().create_future()
        self._pending[approval_id] = future
        return approval_id, future

    def resolve(self, approval_id, decision):
        future = self._pending.get(approval_id)
        if future is None or future.done():
            return False
        future.set_result(decision)
        return True

    def discard(self, approval_id):
        future = self._pending.pop(approval_id, None)
        if future is not None and not future.done():
            future.cancel()

    def pending_count(self):
        return sum(1 for future in self._pending.values() if not future.done())


class ContentFilter:
    """Model matnidagi <think>…</think> va matn ko'rinishidagi <tool_call>…</tool_call> bloklarini ajratadi."""

    TAGS = {"<think>": "</think>", "<tool_call>": "</tool_call>"}

    def __init__(self):
        self.buffer = ""
        self.mode = None
        self.captured = ""
        self.tool_texts = []

    @staticmethod
    def _partial(text, tags):
        keep = 0
        for tag in tags:
            for size in range(min(len(tag) - 1, len(text)), 0, -1):
                if text.endswith(tag[:size]):
                    keep = max(keep, size)
                    break
        return keep

    def feed(self, text):
        self.buffer += text
        out = []
        while self.buffer:
            if self.mode is None:
                positions = [(self.buffer.find(tag), tag) for tag in self.TAGS if tag in self.buffer]
                if positions:
                    index, tag = min(positions)
                    if index:
                        out.append(("text", self.buffer[:index]))
                    self.buffer = self.buffer[index + len(tag):]
                    self.mode = tag
                    continue
                keep = self._partial(self.buffer, self.TAGS)
                emit = self.buffer[:len(self.buffer) - keep]
                if emit:
                    out.append(("text", emit))
                self.buffer = self.buffer[len(self.buffer) - keep:]
                break
            close = self.TAGS[self.mode]
            index = self.buffer.find(close)
            if index >= 0:
                self._take(self.buffer[:index], out)
                if self.mode == "<tool_call>":
                    self.tool_texts.append(self.captured)
                self.captured = ""
                self.buffer = self.buffer[index + len(close):]
                self.mode = None
                continue
            keep = self._partial(self.buffer, [close])
            self._take(self.buffer[:len(self.buffer) - keep], out)
            self.buffer = self.buffer[len(self.buffer) - keep:]
            break
        return out

    def _take(self, text, out):
        if not text:
            return
        if self.mode == "<think>":
            out.append(("thinking", text))
        else:
            self.captured += text

    def flush(self):
        out = []
        rest, self.buffer = self.buffer, ""
        if self.mode is None:
            if rest:
                out.append(("text", rest))
        elif self.mode == "<think>":
            if rest:
                out.append(("thinking", rest))
        else:
            self.tool_texts.append(self.captured + rest)
        self.mode, self.captured = None, ""
        return out

    def tool_calls(self):
        calls = []
        for text in self.tool_texts:
            for candidate in re.findall(r"\{.*\}", text, re.DOTALL) or [text]:
                try:
                    data = json.loads(candidate)
                except ValueError:
                    continue
                if isinstance(data, dict) and data.get("name"):
                    calls.append({"name": data["name"], "arguments": data.get("arguments") or data.get("parameters") or {}})
        return calls


def _event(kind, **payload):
    return {"type": kind, **payload}


def _call_parts(call):
    function = call.get("function") if isinstance(call, dict) else getattr(call, "function", None)
    if function is None:
        return "", {}
    if isinstance(function, dict):
        name, arguments = function.get("name", ""), function.get("arguments", {})
    else:
        name, arguments = getattr(function, "name", ""), getattr(function, "arguments", {})
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments.strip() else {}
        except ValueError:
            arguments = {"_raw": arguments}
    return name, dict(arguments or {})


def _size(message):
    size = len(message.get("content") or "") + 24
    if message.get("tool_calls"):
        size += len(json.dumps(message["tool_calls"], ensure_ascii=False))
    return size


def _compact(message, limit):
    content = message.get("content") or ""
    if len(content) <= limit:
        return message
    return {**message, "content": content[:limit] + "\n… [eski kontekst qisqartirildi]"}


def clean_history(history):
    """Mijozdan kelgan tarixni Ollama formatiga keltiradi va noto'g'ri yozuvlarni tashlaydi."""
    cleaned = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role not in {"user", "assistant", "tool"}:
            continue
        message = {"role": role, "content": str(item.get("content") or "")}
        if role == "assistant" and isinstance(item.get("tool_calls"), list):
            calls = []
            for call in item["tool_calls"]:
                name, arguments = _call_parts(call)
                if name:
                    calls.append({"function": {"name": name, "arguments": arguments}})
            if calls:
                message["tool_calls"] = calls
        if role == "tool":
            if not cleaned or (cleaned[-1]["role"] not in {"assistant", "tool"}):
                continue
            if item.get("tool_name"):
                message["tool_name"] = str(item["tool_name"])
        cleaned.append(message)
    return cleaned


def fit_messages(system, history, current, settings, extra_chars=0):
    """Kontekst oynasiga sig'adigan xabarlar ro'yxatini tuzadi (yangilari ustuvor)."""
    total_chars = int(settings.num_ctx * CHARS_PER_TOKEN)
    reserve = int(min(4096, settings.num_ctx * 0.25) * CHARS_PER_TOKEN)
    budget = total_chars - reserve - len(system) - extra_chars

    current = list(current)
    if current and current[0]["role"] == "user" and len(current[0]["content"]) > budget * 0.8:
        # Juda uzun matn: boshi va oxiri saqlanadi, o'rtasi qisqartiriladi.
        content = current[0]["content"]
        limit = int(budget * 0.8)
        head, tail = int(limit * 0.7), int(limit * 0.3)
        omitted = len(content) - head - tail
        current[0] = {**current[0], "content": (
            content[:head] + f"\n\n… [matn juda uzun: o'rtadagi {omitted:,} belgi tushirib qoldirildi] …\n\n" + content[-tail:]
        )}
    current_size = sum(_size(message) for message in current)
    if current_size > budget:
        # Joriy navbatdagi eski vosita natijalarini qisqartiramiz (oxirgi ikkitasi qoladi).
        tool_indexes = [index for index, message in enumerate(current) if message["role"] == "tool"]
        for index in tool_indexes[:-2]:
            current[index] = _compact(current[index], 1500)
        current_size = sum(_size(message) for message in current)
        if current_size > budget:
            for index in tool_indexes[-2:]:
                current[index] = _compact(current[index], max(2000, budget // 4))
            current_size = sum(_size(message) for message in current)

    turns = []
    for message in history:
        if message["role"] == "user" or not turns:
            turns.append([])
        turns[-1].append(message)

    kept, used = [], current_size
    for age, turn in enumerate(reversed(turns)):
        recent = age == 0
        compacted = []
        for message in turn:
            if message["role"] == "tool":
                limit = 3000 if recent else 1000
            elif message["role"] == "user":
                limit = 10000 if recent else 3000
            else:
                limit = 6000 if recent else 2500
            compacted.append(_compact(message, limit))
        size = sum(_size(message) for message in compacted)
        if used + size > budget:
            break
        kept = compacted + kept
        used += size
    while kept and kept[0]["role"] == "tool":
        kept.pop(0)
    return [{"role": "system", "content": system}] + kept + current


def build_attachments(attachments):
    """Biriktirilgan fayllar mazmunini foydalanuvchi xabariga qo'shish uchun tayyorlaydi."""
    blocks, used = [], 0
    for attachment in attachments:
        path = attachment["path"]
        name = attachment["name"]
        remaining = ATTACHMENTS_TOTAL_CHARS - used
        if remaining < 500:
            blocks.append(f'<file name="{name}" path="{path}">\n[Joy qolmadi: mazmunni vositalar bilan o\'qing.]\n</file>')
            continue
        try:
            kind, text = files.extract_text(path)
        except (files.FileReadError, OSError) as error:
            blocks.append(f'<file name="{name}" path="{path}">\n[O\'qib bo\'lmadi: {error}]\n</file>')
            continue
        limit = min(ATTACHMENT_CHARS, remaining)
        if len(text) > limit:
            hint = "analyze_table" if kind == "table" else "read_file (start_line)"
            text = text[:limit] + f"\n… [fayl qisqartirildi: jami {len(text):,} belgi. Davomini {hint} bilan o'qing.]"
        used += len(text)
        blocks.append(f'<file name="{name}" path="{path}" type="{kind}">\n{text}\n</file>')
    return "\n\n".join(blocks)


class Agent:
    def __init__(self, settings, manager, grants, broker):
        self.settings = settings
        self.manager = manager
        self.grants = grants
        self.broker = broker

    async def run(self, chat_id, history, text, attachments=(), think=False):
        status = await self.manager.status()
        if not status["ready"]:
            yield _event("error", message=status["message"] or "Model tayyor emas.")
            return
        model = status["model"]
        caps = await self.manager.capabilities(model)
        tools_enabled = caps is None or "tools" in caps
        if caps is None:
            think_param = bool(think)
        else:
            think_param = bool(think) if "thinking" in caps else None

        names = [attachment["name"] for attachment in attachments]
        skills, body = select_skills(text, names)
        body = normalize_text(body).strip()
        if not body:
            if attachments:
                body = "Biriktirilgan faylni ko'rib chiq va asosiy mazmunini qisqacha tushuntir."
            elif skills:
                body = f"«{skills[0].name}» ko'nikmasini yoqdim. Nima qilish kerakligini bitta qisqa savol bilan so'ra."
            else:
                yield _event("error", message="Xabar bo'sh. Savolingizni yozing.")
                return
        user_content = body
        if attachments:
            user_content += "\n\n" + await asyncio.to_thread(build_attachments, list(attachments))
        user_message = {"role": "user", "content": user_content}
        # Modelga ketadigan nusxada joriy so'rov ko'rsatmalari bor; tarixga toza xabar yoziladi.
        model_user = {"role": "user", "content": user_content + request_guidelines(skills, time_text())}

        yield _event(
            "meta",
            model=model,
            skills=[skill.public() for skill in skills],
            tools=tools_enabled,
            thinking=think_param is True,
        )
        yield _event("message", message=user_message)

        options = {"num_ctx": self.settings.num_ctx, "top_k": 20}
        temperatures = [skill.temperature for skill in skills if skill.temperature is not None]
        if think_param:
            options.update(temperature=0.6, top_p=0.95)
        else:
            options.update(temperature=min(temperatures) if temperatures else 0.7, top_p=0.8)

        prior = clean_history(history)
        current = [model_user]
        ctx = ToolContext(settings=self.settings, chat_id=chat_id)
        seen, denied = {}, set()
        client = self.manager.client()
        started = time.monotonic()
        stats = {}

        for round_index in range(self.settings.max_tool_rounds + 1):
            use_tools = tools_enabled and round_index < self.settings.max_tool_rounds
            system = system_prompt(self.settings, tools_enabled=tools_enabled, today=today_text())
            messages = fit_messages(
                system, prior, current, self.settings, extra_chars=TOOL_SCHEMA_CHARS if use_tools else 0,
            )
            content, calls = "", []
            content_filter = ContentFilter()
            try:
                async for kind, payload in self._stream(client, model, messages, use_tools, think_param, options):
                    if kind == "notice":
                        if payload == "no-tools":
                            tools_enabled = use_tools = False
                            self.manager.forget_capability(model, "tools")
                        elif payload == "no-thinking":
                            think_param = None
                            self.manager.forget_capability(model, "thinking")
                        continue
                    if kind == "thinking":
                        yield _event("thinking", delta=payload)
                    elif kind == "content":
                        for part_kind, part in content_filter.feed(payload):
                            if part_kind == "text":
                                content += part
                                yield _event("token", delta=part)
                            else:
                                yield _event("thinking", delta=part)
                    elif kind == "tool_calls":
                        calls.extend(payload)
                    elif kind == "stats":
                        stats = payload
            except asyncio.CancelledError:
                raise
            except Exception as error:
                yield _event("error", message=self._error_text(error, model))
                return
            for part_kind, part in content_filter.flush():
                if part_kind == "text":
                    content += part
                    yield _event("token", delta=part)
                else:
                    yield _event("thinking", delta=part)

            parsed = [_call_parts(call) for call in calls]
            if not parsed and use_tools:
                parsed = [(call["name"], dict(call["arguments"])) for call in content_filter.tool_calls()]
            parsed = [(name, args) for name, args in parsed if name]

            assistant = {"role": "assistant", "content": content.strip()}
            if parsed and use_tools:
                assistant["tool_calls"] = [{"function": {"name": name, "arguments": args}} for name, args in parsed]
            current.append(assistant)
            yield _event("message", message=assistant)

            if not parsed or not use_tools:
                if not content.strip():
                    yield _event("error", message="Model bo'sh javob qaytardi. Savolni boshqacha yozib ko'ring.")
                break

            for name, args in parsed:
                async for event in self._run_tool(ctx, name, args, seen, denied, current):
                    yield event

        elapsed = round(time.monotonic() - started, 1)
        yield _event("done", elapsed=elapsed, tokens=stats.get("eval_count"))

    async def _stream(self, client, model, messages, use_tools, think, options):
        tools = tool_schemas() if use_tools else None
        for _ in range(3):
            yielded = False
            try:
                stream = await client.chat(
                    model=model, messages=messages, tools=tools, stream=True, think=think, options=options,
                    keep_alive="30m",
                )
                async for chunk in stream:
                    message = chunk.message
                    if getattr(message, "thinking", None):
                        yielded = True
                        yield "thinking", message.thinking
                    if message.content:
                        yielded = True
                        yield "content", message.content
                    if message.tool_calls:
                        yielded = True
                        yield "tool_calls", list(message.tool_calls)
                    if chunk.done:
                        yield "stats", {"eval_count": getattr(chunk, "eval_count", None)}
                return
            except ollama.ResponseError as error:
                text = str(getattr(error, "error", error)).lower()
                if yielded:
                    raise
                if tools and "support tools" in text:
                    tools = None
                    yield "notice", "no-tools"
                    continue
                if think is not None and "thinking" in text:
                    think = None
                    yield "notice", "no-thinking"
                    continue
                raise

    async def _run_tool(self, ctx, name, args, seen, denied, current):
        tool = find_tool(name)
        tool_id = secrets.token_hex(4)
        key = json.dumps([tool.name if tool else name, args], sort_keys=True, ensure_ascii=False, default=str)

        def finish(content):
            message = {"role": "tool", "content": content, "tool_name": tool.name if tool else name}
            current.append(message)
            history_message = _compact(message, HISTORY_TOOL_CHARS)
            return _event("message", message=history_message)

        if tool is None:
            yield finish(f"Xato: '{name}' degan vosita yo'q. Mavjud vositalar: list_directory, read_file, "
                         "search_files, analyze_table, write_file, calculate.")
            return
        if key in denied:
            yield finish("Foydalanuvchi bu amalni rad etgan. Uni qayta so'ramang.")
            return
        if key in seen:
            yield finish("Bu vosita aynan shu parametrlar bilan allaqachon chaqirilgan, natija yuqorida bor. "
                         "Endi javob bering yoki boshqa qadam tanlang.")
            return

        try:
            prepared = tool.prepare(ctx, args)
        except ToolError as error:
            yield _event("tool", id=tool_id, name=tool.name, icon=tool.icon, action=tool.action,
                         target=str(args.get("path") or args.get("expression") or ""), status="running")
            yield _event("tool_done", id=tool_id, status="error", summary=str(error))
            yield finish(f"Xato: {error}")
            return

        target = target_label(prepared)
        yield _event("tool", id=tool_id, name=tool.name, icon=tool.icon, action=tool.action, target=target,
                     status="running", detail=self._detail(tool.name, prepared))

        if needs_approval(tool, prepared, ctx, self.grants):
            decision = None
            async for item in self._ask(tool, tool_id, prepared, target):
                if isinstance(item, dict):
                    yield item
                else:
                    decision = item
            if decision not in {"allow", "allow_folder"}:
                denied.add(key)
                yield _event("tool_done", id=tool_id, status="denied", summary="Rad etildi")
                yield finish(
                    f"Foydalanuvchi {target} uchun ruxsat bermadi. Shu amalni qayta urinmang; "
                    "mavjud ma'lumot bilan javob bering yoki boshqa yo'l so'rang."
                )
                return
            if decision == "allow_folder" and tool.access == "read" and not prepared.sensitive:
                self.grants.grant(ctx.chat_id, prepared.folder)

        try:
            result = await asyncio.to_thread(tool.run, ctx, prepared)
        except ToolError as error:
            yield _event("tool_done", id=tool_id, status="error", summary=str(error))
            yield finish(f"Xato: {error}")
            return
        except Exception as error:  # Kutilmagan xatolar ham agentni to'xtatmasin.
            yield _event("tool_done", id=tool_id, status="error", summary=f"Kutilmagan xato: {error}")
            yield finish(f"Xato: kutilmagan muammo — {error}")
            return
        seen[key] = True
        yield _event("tool_done", id=tool_id, status="done", summary=result.summary, preview=result.preview[:4000])
        yield finish(result.content)

    async def _ask(self, tool, tool_id, prepared, target):
        approval_id, future = self.broker.create()
        try:
            yield _event(
                "approval",
                id=approval_id,
                tool_id=tool_id,
                name=tool.name,
                icon=tool.icon,
                action=tool.action,
                access=tool.access,
                path=target,
                folder=display_path(prepared.folder) if tool.access == "read" and not prepared.sensitive else None,
                sensitive=prepared.sensitive,
                exists=prepared.exists,
                detail=self._detail(tool.name, prepared),
                note=prepared.note,
                preview=prepared.preview,
            )
            deadline = time.monotonic() + self.settings.approval_timeout
            while not future.done():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                await asyncio.wait({future}, timeout=min(15, remaining))
                if not future.done():
                    yield _event("ping")
            decision = future.result() if future.done() and not future.cancelled() else "deny"
            yield _event("approval_done", id=approval_id, decision=decision)
            yield decision
        finally:
            self.broker.discard(approval_id)

    @staticmethod
    def _detail(name, prepared):
        args = prepared.args
        if name == "search_files":
            parts = []
            if args.get("name"):
                parts.append(f"nomi: «{args['name']}»")
            if args.get("text"):
                parts.append(f"matn: «{args['text']}»")
            return "Qidiruv — " + ", ".join(parts)
        if name == "list_directory" and args.get("depth"):
            return f"Chuqurlik: {args['depth']}"
        if name == "write_file":
            return "Mavjud fayl ustidan yoziladi" if prepared.exists else "Yangi fayl yaratiladi"
        if name == "analyze_table" and args.get("sheet"):
            return f"Varaq: {args['sheet']}"
        return ""

    def _error_text(self, error, model):
        if isinstance(error, (httpx.ConnectError, ConnectionError)):
            return "Ollama bilan aloqa uzildi. Ollama ishlayotganini tekshiring (`ollama serve`)."
        if isinstance(error, (httpx.TimeoutException, asyncio.TimeoutError)):
            return "Model javob berishga ulgurmadi (vaqt tugadi). Qayta urinib ko'ring."
        if isinstance(error, ollama.ResponseError):
            text = str(getattr(error, "error", error))
            if getattr(error, "status_code", None) == 404 or "not found" in text.lower():
                return f"Model topilmadi: {model}. Terminalda `ollama pull {self.settings.base_model}` buyrug'ini bajaring."
            if "memory" in text.lower():
                return "Modelni ishga tushirish uchun xotira yetmadi. Boshqa dasturlarni yopib, qayta urinib ko'ring."
            return "Ollama xatosi: " + text
        return f"Kutilmagan xato: {error}"
