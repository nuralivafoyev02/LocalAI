"""Model chaqira oladigan vositalar (tools) va ularning ruxsat talablari."""

import difflib
import fnmatch
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import files
from .calculator import calculate
from .permissions import PathError, display_path, is_sensitive, is_within, resolve_path


class ToolError(Exception):
    pass


@dataclass
class ToolContext:
    settings: object
    chat_id: str


@dataclass
class Prepared:
    """Bajarishdan oldin tekshirilgan chaqiruv: qaysi yo'lga, qanday ruxsat kerak."""

    args: dict
    path: Path = None
    folder: Path = None
    access: str = "none"  # none | read | write
    note: str = ""
    sensitive: bool = False
    exists: bool = True
    preview: str = ""


@dataclass
class ToolResult:
    content: str
    summary: str
    preview: str = ""
    ok: bool = True


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    access: str
    action: str
    icon: str
    prepare: object
    run: object
    extra: dict = field(default_factory=dict)

    def schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def _clip(text, limit):
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n… [natija qisqartirildi: jami {len(text):,} belgi, ko'rsatildi {limit:,}]"


def _prepare_path(ctx, args, key="path", access="read", must_exist=True):
    raw = args.get(key)
    if raw in (None, ""):
        if key == "path" and access == "read":
            raw = "."
        else:
            raise ToolError(f"'{key}' parametri kerak.")
    try:
        path, note = resolve_path(raw, ctx.settings.workspace)
    except PathError as error:
        raise ToolError(str(error)) from error
    exists = path.exists()
    if must_exist and not exists:
        raise ToolError(f"Yo'l topilmadi: {display_path(path)}")
    folder = path if path.is_dir() else path.parent
    return Prepared(
        args=args, path=path, folder=folder, access=access, note=note,
        sensitive=is_sensitive(path), exists=exists,
    )


def _int(value, default, low, high):
    try:
        return max(low, min(int(value), high))
    except (TypeError, ValueError):
        return default


def _bool(value):
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ha"}
    return bool(value)


def _with_note(prepared, text):
    return (prepared.note + "\n\n" + text) if prepared.note else text


# ------------------------------------------------------------ list_directory

def _list_prepare(ctx, args):
    prepared = _prepare_path(ctx, args)
    if not prepared.path.is_dir():
        raise ToolError(f"Bu papka emas, fayl: {display_path(prepared.path)}. Uni read_file bilan o'qing.")
    return prepared


def _list_run(ctx, prepared):
    root = prepared.path
    depth = _int(prepared.args.get("depth"), 1, 1, 4)
    show_hidden = _bool(prepared.args.get("show_hidden"))
    lines = [f"{display_path(root)}/"]
    counts = {"files": 0, "dirs": 0, "total_size": 0}
    limit = 400

    def walk(folder, level, prefix):
        try:
            entries = sorted(os.scandir(folder), key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
        except PermissionError:
            lines.append(prefix + "[ruxsat yo'q]")
            return
        except OSError as error:
            lines.append(prefix + f"[o'qib bo'lmadi: {error.strerror}]")
            return
        visible = [e for e in entries if show_hidden or not e.name.startswith(".")]
        hidden = len(entries) - len(visible)
        for entry in visible:
            if len(lines) > limit:
                lines.append(prefix + "… (ro'yxat juda uzun, chuqurlikni kamaytiring yoki ichki papkani oching)")
                return
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError:
                is_dir = False
            if is_dir:
                counts["dirs"] += 1
                skipped = entry.name in files.SKIP_DIRS
                lines.append(f"{prefix}{entry.name}/" + ("  (o'tkazib yuborildi)" if skipped and level < depth else ""))
                if level < depth and not skipped and not entry.is_symlink():
                    walk(entry.path, level + 1, prefix + "  ")
            else:
                counts["files"] += 1
                try:
                    size = entry.stat(follow_symlinks=False).st_size
                except OSError:
                    size = 0
                counts["total_size"] += size
                lines.append(f"{prefix}{entry.name}  ({files.human_size(size)})")
        if hidden:
            lines.append(f"{prefix}(+{hidden} yashirin element)")

    walk(root, 1, "  ")
    summary = f"{counts['dirs']} papka, {counts['files']} fayl"
    text = "\n".join(lines) + f"\n\nJami: {summary}, fayllar hajmi {files.human_size(counts['total_size'])}."
    return ToolResult(
        content=_clip(_with_note(prepared, text), ctx.settings.tool_output_chars),
        summary=summary,
        preview="\n".join(lines[:40]),
    )


# ------------------------------------------------------------------ read_file

def _read_prepare(ctx, args):
    prepared = _prepare_path(ctx, args)
    if prepared.path.is_dir():
        raise ToolError(f"Bu papka: {display_path(prepared.path)}. Uni list_directory bilan ko'ring.")
    return prepared


def _read_run(ctx, prepared):
    path = prepared.path
    try:
        kind, text = files.extract_text(path)
    except files.FileReadError as error:
        raise ToolError(str(error)) from error
    except OSError as error:
        raise ToolError(f"Faylni o'qib bo'lmadi: {error.strerror or error}") from error

    if kind == "table":
        header = f"{display_path(path)} — jadval fayli. Aniq hisob-kitoblar uchun analyze_table dan foydalaning.\n\n"
        return ToolResult(
            content=_clip(_with_note(prepared, header + text), ctx.settings.tool_output_chars),
            summary="jadval ko'rinishi",
            preview=text[:1500],
        )

    lines = text.splitlines()
    total = len(lines)
    start = _int(prepared.args.get("start_line"), 1, 1, max(total, 1))
    max_lines = _int(prepared.args.get("max_lines"), 400, 1, 2000)
    chunk = lines[start - 1:start - 1 + max_lines]
    budget = ctx.settings.tool_output_chars - 400
    numbered, used, end = [], 0, start - 1
    width = len(str(start + len(chunk)))
    for offset, line in enumerate(chunk):
        if len(line) > 2000:
            line = line[:2000] + " …"
        item = f"{str(start + offset).rjust(width)}│ {line}"
        if used + len(item) > budget and numbered:
            break
        numbered.append(item)
        used += len(item) + 1
        end = start + offset
    size = files.human_size(path.stat().st_size)
    header = f"{display_path(path)} ({size}, {total} qator"
    header += f"; {start}–{end} qatorlar ko'rsatildi)" if (start > 1 or end < total) else ")"
    body = "\n".join(numbered) if numbered else "(fayl bo'sh)"
    footer = ""
    if end < total:
        footer = f"\n\n[Davomi bor: keyingi qismni o'qish uchun start_line={end + 1} bering.]"
    return ToolResult(
        content=_with_note(prepared, header + "\n" + body + footer),
        summary=f"{total} qator" if end >= total and start == 1 else f"{start}–{end} / {total} qator",
        preview="\n".join(chunk[:30]),
    )


# --------------------------------------------------------------- search_files

def _search_prepare(ctx, args):
    prepared = _prepare_path(ctx, args)
    if not prepared.path.is_dir():
        raise ToolError("Qidiruv uchun papka yo'li kerak.")
    if not (args.get("name") or args.get("text")):
        raise ToolError("'name' (fayl nomi namunasi) yoki 'text' (fayl ichidagi matn) parametrlaridan kamida bittasi kerak.")
    return prepared


def _search_run(ctx, prepared):
    root = prepared.path
    name = str(prepared.args.get("name") or "").strip()
    text = str(prepared.args.get("text") or "").strip()
    max_results = _int(prepared.args.get("max_results"), 40, 1, 100)
    if name and not any(char in name for char in "*?["):
        name_pattern = f"*{name}*"
    else:
        name_pattern = name
    needle = text.lower()
    results, scanned, near = [], 0, []
    for folder, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in files.SKIP_DIRS and not d.startswith("."))
        for filename in sorted(filenames):
            if len(results) >= max_results or scanned >= 20000:
                break
            scanned += 1
            path = Path(folder) / filename
            if name_pattern and not fnmatch.fnmatch(filename.lower(), name_pattern.lower()):
                if name and len(near) < 5 and difflib.SequenceMatcher(None, name.lower(), filename.lower()).ratio() > 0.75:
                    near.append(path)
                continue
            if not text:
                results.append(display_path(path))
                continue
            if is_sensitive(path) or (path.is_symlink() and not is_within(path.resolve(), root)):
                continue
            try:
                if path.stat().st_size > 2 * 1024 * 1024:
                    continue
                with open(path, "rb") as handle:
                    data = handle.read()
            except OSError:
                continue
            if files.is_binary(data[:4096]):
                continue
            content = files.decode_bytes(data)
            hits = []
            for number, line in enumerate(content.splitlines(), start=1):
                if needle in line.lower():
                    hits.append(f"  {number}: {line.strip()[:200]}")
                    if len(hits) >= 5:
                        break
            if hits:
                results.append(display_path(path) + "\n" + "\n".join(hits))
        if len(results) >= max_results or scanned >= 20000:
            break
    if results:
        body = "\n".join(results)
        summary = f"{len(results)} ta natija"
    else:
        body = "Hech narsa topilmadi."
        if near:
            body += " O'xshash nomlar: " + ", ".join(display_path(p) for p in near)
        summary = "topilmadi"
    if len(results) >= max_results:
        body += f"\n\n(Natijalar {max_results} ta bilan cheklandi.)"
    return ToolResult(
        content=_clip(_with_note(prepared, f"Qidiruv: {display_path(root)}\n" + body), ctx.settings.tool_output_chars),
        summary=summary,
        preview=body[:1500],
    )


# -------------------------------------------------------------- analyze_table

def _table_prepare(ctx, args):
    prepared = _read_prepare(ctx, args)
    suffix = prepared.path.suffix.lower()
    if suffix not in files.TABLE_SUFFIXES | {".json"}:
        raise ToolError("analyze_table faqat CSV, TSV, XLSX, XLS va JSON fayllar uchun. Boshqa fayllarni read_file bilan o'qing.")
    return prepared


def _table_run(ctx, prepared):
    args = prepared.args
    try:
        frames = files.load_tables(prepared.path)
        query_keys = ("columns", "filters", "group_by", "aggregate", "sort_by")
        if not any(args.get(key) for key in query_keys):
            text = files.table_overview(frames, prepared.path.name, args.get("sheet"), preview_rows=20)
            summary = "umumiy tahlil"
        else:
            sheet = files.pick_sheet(frames, args.get("sheet"))
            frame = frames[sheet]
            result, limit, notes = files.query_table(
                frame,
                columns=args.get("columns"),
                filters=args.get("filters"),
                group_by=args.get("group_by"),
                aggregate=args.get("aggregate"),
                sort_by=args.get("sort_by"),
                descending=_bool(args.get("descending")),
                limit=args.get("limit"),
            )
            text = f"Fayl: {prepared.path.name}" + (f", varaq: {sheet}" if len(frames) > 1 else "")
            text += f"\nNatija: {len(result):,} qator\n"
            if notes:
                text += "\n".join(notes) + "\n"
            text += "\n" + files.frame_to_markdown(result, limit)
            summary = f"{len(result):,} qatorli natija"
    except files.FileReadError as error:
        raise ToolError(str(error)) from error
    except ImportError as error:
        raise ToolError(f"Kerakli kutubxona o'rnatilmagan: {error}") from error
    except Exception as error:
        raise ToolError(f"Jadvalni tahlil qilib bo'lmadi: {error}") from error
    return ToolResult(
        content=_clip(_with_note(prepared, text), ctx.settings.tool_output_chars),
        summary=summary,
        preview=text[:2000],
    )


# ----------------------------------------------------------------- write_file

def _write_prepare(ctx, args):
    content = args.get("content")
    if content is None:
        raise ToolError("'content' parametri kerak.")
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False, indent=2)
    if len(content.encode("utf-8")) > 2 * 1024 * 1024:
        raise ToolError("Fayl mazmuni 2 MB dan katta.")
    prepared = _prepare_path(ctx, args, access="write", must_exist=False)
    if prepared.path.is_dir():
        raise ToolError("Bu papka yo'li. Fayl nomini ham ko'rsating.")
    prepared.args = dict(args, content=content)
    lines = content.splitlines()
    preview = "\n".join(lines[:60])
    if len(lines) > 60:
        preview += f"\n… (+{len(lines) - 60} qator)"
    prepared.preview = preview
    return prepared


def _write_run(ctx, prepared):
    path = prepared.path
    content = prepared.args["content"]
    existed = path.exists()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.localai-tmp")
        temp.write_text(content, encoding="utf-8")
        os.replace(temp, path)
    except OSError as error:
        raise ToolError(f"Faylni yozib bo'lmadi: {error.strerror or error}") from error
    lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    action = "yangilandi" if existed else "yaratildi"
    return ToolResult(
        content=f"Fayl {action}: {display_path(path)} ({lines} qator, {files.human_size(len(content.encode('utf-8')))}).",
        summary=f"{action} · {lines} qator",
        preview=prepared.preview,
    )


# ------------------------------------------------------------------ calculate

def _calc_prepare(ctx, args):
    expression = args.get("expression")
    if expression in (None, ""):
        raise ToolError("'expression' parametri kerak.")
    return Prepared(args={"expression": str(expression)})


def _calc_run(ctx, prepared):
    expression = prepared.args["expression"]
    try:
        value = calculate(expression)
    except ValueError as error:
        raise ToolError(f"Hisoblab bo'lmadi: {error}") from error
    return ToolResult(content=f"{expression} = {value}", summary=f"= {value}")


TOOLS = [
    Tool(
        name="list_directory",
        description=(
            "List the files and subfolders of a folder on the user's computer (with sizes). "
            "Use first when exploring a folder or project. depth=2 shows nested folders."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Folder path, e.g. ~/Desktop, ~/projects/app or an absolute path"},
                "depth": {"type": "integer", "description": "How many levels deep to list (1-4, default 1)"},
                "show_hidden": {"type": "boolean", "description": "Include hidden dot-files"},
            },
            "required": ["path"],
        },
        access="read", action="Papkani ko'rish", icon="folder",
        prepare=_list_prepare, run=_list_run,
    ),
    Tool(
        name="read_file",
        description=(
            "Read a file from the user's computer: text, code, Markdown, JSON, PDF, DOCX, Jupyter notebooks. "
            "Spreadsheets return an overview. Long files are paged with start_line."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "start_line": {"type": "integer", "description": "First line to read (default 1)"},
                "max_lines": {"type": "integer", "description": "Maximum number of lines (default 400)"},
            },
            "required": ["path"],
        },
        access="read", action="Faylni o'qish", icon="file",
        prepare=_read_prepare, run=_read_run,
    ),
    Tool(
        name="search_files",
        description=(
            "Search inside a folder (recursively) for files whose name matches a pattern "
            "and/or whose content contains a text."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Folder to search in"},
                "name": {"type": "string", "description": "File name or glob pattern, e.g. *.py or report"},
                "text": {"type": "string", "description": "Text to find inside files (case-insensitive)"},
                "max_results": {"type": "integer", "description": "Maximum results (default 40)"},
            },
            "required": ["path"],
        },
        access="read", action="Fayllarda qidirish", icon="search",
        prepare=_search_prepare, run=_search_run,
    ),
    Tool(
        name="analyze_table",
        description=(
            "Analyze a spreadsheet or data file (CSV, TSV, XLSX, XLS, JSON). Without options returns structure, "
            "statistics and preview. Use filters, group_by, aggregate and sort_by for exact answers "
            "(totals, averages, counts, top-N, rows matching conditions) computed over the whole file."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Data file path"},
                "sheet": {"type": "string", "description": "Excel sheet name (optional)"},
                "columns": {"type": "array", "items": {"type": "string"}, "description": "Columns to show"},
                "filters": {
                    "type": "array",
                    "description": "Row conditions, all must match",
                    "items": {
                        "type": "object",
                        "properties": {
                            "column": {"type": "string"},
                            "op": {"type": "string", "enum": sorted(files.FILTER_OPS)},
                            "value": {"description": "Value to compare with"},
                        },
                        "required": ["column", "op"],
                    },
                },
                "group_by": {"type": "array", "items": {"type": "string"}, "description": "Columns to group by"},
                "aggregate": {
                    "type": "array",
                    "description": "Aggregations; use column '*' with func 'count' to count rows",
                    "items": {
                        "type": "object",
                        "properties": {
                            "column": {"type": "string"},
                            "func": {"type": "string", "enum": sorted(files.AGG_FUNCS)},
                        },
                        "required": ["column", "func"],
                    },
                },
                "sort_by": {"type": "string", "description": "Column to sort the result by"},
                "descending": {"type": "boolean", "description": "Sort from largest to smallest"},
                "limit": {"type": "integer", "description": "Max rows to return (default 50)"},
            },
            "required": ["path"],
        },
        access="read", action="Jadvalni tahlil qilish", icon="table",
        prepare=_table_prepare, run=_table_run,
    ),
    Tool(
        name="write_file",
        description=(
            "Create or overwrite a text file on the user's computer (code, notes, reports). "
            "Use only when the user asks to create or save a file. The user reviews it first."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Destination file path"},
                "content": {"type": "string", "description": "Full file content"},
            },
            "required": ["path", "content"],
        },
        access="write", action="Faylga yozish", icon="pencil",
        prepare=_write_prepare, run=_write_run,
    ),
    Tool(
        name="calculate",
        description=(
            "Evaluate a math expression exactly: + - * / ** %, parentheses, sqrt, log, sin, round, "
            "factorial, mean, median, percent(p, total). Use for any non-trivial arithmetic."
        ),
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "e.g. (1250000 * 12) * 0.88 or sqrt(2) ** 10"},
            },
            "required": ["expression"],
        },
        access="none", action="Hisoblash", icon="calculator",
        prepare=_calc_prepare, run=_calc_run,
    ),
]

TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}
TOOL_ALIASES = {
    "ls": "list_directory", "list_dir": "list_directory", "list_files": "list_directory",
    "list_folder": "list_directory", "read": "read_file", "open_file": "read_file",
    "cat": "read_file", "grep": "search_files", "find_files": "search_files",
    "search": "search_files", "read_table": "analyze_table", "analyze_excel": "analyze_table",
    "calculator": "calculate", "calc": "calculate", "math": "calculate", "save_file": "write_file",
    "create_file": "write_file",
}


def find_tool(name):
    name = str(name or "").strip()
    if name in TOOLS_BY_NAME:
        return TOOLS_BY_NAME[name]
    if name.lower() in TOOL_ALIASES:
        return TOOLS_BY_NAME[TOOL_ALIASES[name.lower()]]
    match = difflib.get_close_matches(name.lower(), list(TOOLS_BY_NAME), n=1, cutoff=0.7)
    return TOOLS_BY_NAME[match[0]] if match else None


def tool_schemas():
    return [tool.schema() for tool in TOOLS]


def is_upload(path, settings):
    return is_within(path, settings.upload_dir.resolve())


def needs_approval(tool, prepared, ctx, grants):
    if tool.access == "none":
        return False
    if tool.access == "write":
        return True
    if is_upload(prepared.path, ctx.settings) and not prepared.sensitive:
        return False
    return not grants.allows(ctx.chat_id, prepared.path)


def target_label(prepared):
    if prepared.path is None:
        return prepared.args.get("expression", "")
    return display_path(prepared.path)


def today_text():
    return datetime.now().astimezone().strftime("%Y-%m-%d (%A)")


def time_text():
    return datetime.now().astimezone().strftime("%H:%M %Z").strip()
