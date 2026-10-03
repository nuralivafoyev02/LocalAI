"""Skill'lar: maxsus ko'nikmalar. Slash-buyruq bilan yoki xabar mazmunidan avtomatik yoqiladi."""

import difflib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    command: str
    icon: str
    description: str
    keywords: tuple
    prompt: str
    example: str = ""
    temperature: float = None

    def public(self):
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "icon": self.icon,
            "description": self.description,
            "example": self.example,
        }


SKILLS = (
    Skill(
        id="code",
        name="Kod",
        command="/kod",
        icon="code",
        description="Kod yozish, xatoni topish, tushuntirish va refaktoring",
        example="Python'da fayllarni kengaytmasi bo'yicha papkalarga ajratadigan skript yoz",
        temperature=0.3,
        keywords=(
            "kod", "kodni", "kodini", "kodim", "kodda", "kodga", "code", "dastur", "dasturlash",
            "programma", "program", "python", "pyton",
            "javascript", "typescript", "java", "kotlin", "swift", "golang", "rust", "php",
            "ruby", "sql", "html", "css", "react", "vue", "angular", "node", "nodejs", "django",
            "flask", "fastapi", "laravel", "funksiya", "function", "klass", "class", "metod",
            "script", "skript", "bug", "debug", "traceback", "exception", "error", "api",
            "algoritm", "algorithm", "regex", "bash", "terminal", "git", "docker", "kompilyator",
            "compile", "refaktor", "refactor", "massiv", "array", "sikl", "loop", "frontend",
            "backend", "telegram bot", "bot", "endpoint", "json", "yaml", "c++", "c#", "dart",
            "flutter", "android", "ios", "linux", "npm", "pip", "код", "программа", "функция",
        ),
        prompt=(
            "## Skill: Coding\n"
            "- Act as a senior software engineer. Write complete, correct, runnable code — no placeholders like "
            "'...' or 'TODO: implement'. Include imports and a short usage example when helpful.\n"
            "- Use fenced code blocks with the right language tag. One file per block; put the file name in a line "
            "above the block when there are several files.\n"
            "- Briefly explain the approach before the code (1-3 sentences) and key points after it. "
            "Code comments in the user's language.\n"
            "- When fixing a bug: identify the root cause first, then show the fixed code and why it works.\n"
            "- Prefer standard libraries and simple, readable solutions; mention edge cases, security pitfalls and "
            "how to run or test the code.\n"
            "- If the user's code is in a local project, read the relevant files with tools before answering.\n"
            "- Save code to disk with write_file only when the user asks to create or save a file."
        ),
    ),
    Skill(
        id="data",
        name="Tahlil",
        command="/tahlil",
        icon="table",
        description="Excel, CSV va JSON ma'lumotlarini tahlil qilish",
        example="Biriktirilgan Excel faylini tahlil qilib, asosiy xulosalarni ayt",
        temperature=0.3,
        keywords=(
            "excel", "xlsx", "xls", "csv", "jadval", "table", "statistika", "tahlil", "analiz",
            "analysis", "ustun", "qator", "hisobot", "report", "dataset", "ma'lumotlar", "data",
            "sotuv", "savdo", "daromad", "xarajat", "o'rtacha", "jami", "summa", "grafik",
            "diagramma", "trend", "foyda", "tushum", "budjet", "budget", "таблица", "анализ",
        ),
        prompt=(
            "## Skill: Data analysis\n"
            "- For any spreadsheet/CSV/JSON question use analyze_table (path of the attached or local file). "
            "Compute exact totals, averages, counts and rankings with filters/group_by/aggregate — never estimate "
            "from a preview.\n"
            "- Structure: short answer first, then a compact Markdown table of key numbers, then 2-4 insights "
            "(trends, outliers, data-quality issues such as empty cells or duplicates).\n"
            "- Never invent units or currencies that are not in the data; say which columns you used."
        ),
    ),
    Skill(
        id="files",
        name="Fayllar",
        command="/papka",
        icon="folder",
        description="Kompyuterdagi papka va fayllarni ko'rib, tahlil qilish",
        example="~/Desktop papkasida nimalar borligini ko'rib, qisqacha tahlil qil",
        keywords=(
            "papka", "folder", "fayl", "file", "katalog", "directory", "loyiha", "project",
            "repozitoriy", "repo", "desktop", "ish stoli", "documents", "hujjatlar", "downloads",
            "yuklanmalar", "readme", "папка", "файл",
        ),
        prompt=(
            "## Skill: Local files and projects\n"
            "- Explore with tools instead of guessing: list_directory (depth 2 for projects), then read the most "
            "informative files (README, package.json / pyproject.toml / requirements.txt, entry points, configs). "
            "Use search_files to locate things.\n"
            "- When describing a project: purpose, tech stack, structure (key folders and files), how to run it, "
            "and notable issues or improvement ideas.\n"
            "- Mention concrete paths. Do not dump whole files back to the user unless asked."
        ),
    ),
    Skill(
        id="spelling",
        name="Imlo",
        command="/imlo",
        icon="spell",
        description="Matndagi imlo, grammatika va punktuatsiya xatolarini tuzatish",
        example="/imlo bugun men maktabga bordm va u yerda dostlarim bilan uchrashdm",
        temperature=0.2,
        keywords=(
            "imlo", "imloviy", "grammatika", "grammar", "punktuatsiya", "orfografiya", "tahrir",
            "to'g'rila", "tuzat", "xatolarini", "proofread", "spelling", "орфография", "грамматика",
        ),
        prompt=(
            "## Skill: Spelling and grammar correction\n"
            "- Return the fully corrected text first (in a quote block), keeping the author's meaning, tone and "
            "language. For Uzbek use the official Latin orthography (o', g', sh, ch, ng; tutuq belgisi ').\n"
            "- Then list the important corrections as 'xato → to'g'ri' with a very short reason. "
            "If there are no errors, say so."
        ),
    ),
    Skill(
        id="translate",
        name="Tarjima",
        command="/tarjima",
        icon="globe",
        description="O'zbek, rus, ingliz va boshqa tillar o'rtasida tarjima",
        example="/tarjima inglizchaga: Ertaga soat 10 da uchrashamiz",
        temperature=0.3,
        keywords=(
            "tarjima", "translate", "translation", "inglizchaga", "ruschaga", "o'zbekchaga",
            "inglizcha", "ruscha", "o'zbekcha", "english", "russian", "turkchaga", "перевод",
            "переведи",
        ),
        prompt=(
            "## Skill: Translation\n"
            "- Translate naturally and accurately, preserving meaning, tone, formatting and names. "
            "If the target language is not stated: Uzbek → English, anything else → Uzbek.\n"
            "- Output the translation first; add short notes only for ambiguous words or idioms."
        ),
    ),
    Skill(
        id="summary",
        name="Xulosa",
        command="/xulosa",
        icon="list",
        description="Matn, fayl yoki hujjatning qisqa mazmuni",
        example="/xulosa biriktirilgan hujjatning asosiy fikrlarini 5 bandda yoz",
        keywords=(
            "xulosa", "qisqacha", "qisqa", "mazmun", "mazmunini", "summary", "summarize",
            "konspekt", "tl;dr", "asosiy fikr", "резюме", "кратко",
        ),
        prompt=(
            "## Skill: Summarization\n"
            "- Start with a one-sentence gist, then 3-7 bullet points with the key facts, numbers and decisions, "
            "then action items if any. Be faithful to the source; do not add facts."
        ),
    ),
    Skill(
        id="math",
        name="Hisob",
        command="/hisob",
        icon="calculator",
        description="Aniq hisob-kitob, foizlar, formulalar va masalalar",
        example="/hisob 12 500 000 so'mning 12% i qancha va qolgani necha?",
        temperature=0.2,
        keywords=(
            "hisobla", "hisob", "calculate", "foiz", "percent", "tenglama", "formula", "masala",
            "kvadrat", "ildiz", "integral", "hosila", "matematika", "math", "kredit", "ustama",
            "chegirma", "soliq", "посчитай", "процент",
        ),
        prompt=(
            "## Skill: Math and calculations\n"
            "- Solve step by step. Use the calculate tool for every non-trivial arithmetic step instead of mental "
            "math, then present the steps and the final result clearly (bold the final answer)."
        ),
    ),
    Skill(
        id="explain",
        name="Tushuntir",
        command="/tushuntir",
        icon="bulb",
        description="Murakkab mavzuni oddiy tilda, misollar bilan tushuntirish",
        example="/tushuntir sun'iy intellekt qanday ishlaydi?",
        keywords=(
            "tushuntir", "tushuntirib", "explain", "nima degani", "nima bu", "qanday ishlaydi",
            "nimaga", "nega", "farqi", "объясни",
        ),
        prompt=(
            "## Skill: Explaining\n"
            "- Explain simply, as to a smart beginner: start with the core idea in one or two sentences, then build "
            "up with a concrete everyday example or analogy, then the important details. Avoid jargon or define it."
        ),
    ),
)

SKILLS_BY_ID = {skill.id: skill for skill in SKILLS}
COMMANDS = {skill.command.lstrip("/"): skill for skill in SKILLS}
COMMAND_ALIASES = {
    "code": "kod", "data": "tahlil", "excel": "tahlil", "folder": "papka", "fayl": "papka",
    "files": "papka", "spell": "imlo", "grammar": "imlo", "translate": "tarjima",
    "summary": "xulosa", "summarize": "xulosa", "math": "hisob", "calc": "hisob",
    "explain": "tushuntir",
}

APOSTROPHES = "ʻʼ‘’`´ʹ′"
CODE_PATTERN = re.compile(
    r"```|\bdef \w+\(|\bfunction \w*\(|\bclass \w+[:({]|\bimport \w+|#include|console\.log|=>|"
    r"\bpublic static\b|Traceback \(most recent call last\)|\w+Error:|\bSELECT\b.+\bFROM\b",
    re.IGNORECASE,
)
MATH_PATTERN = re.compile(
    r"(?<![\w/.-])\d+(?:[.,]\d+)?\s*(?:[+*/×÷^]|\s-\s)\s*\(?\d+(?:[.,]\d+)?(?![\w/-])|(?<![\w/])\d+\s*%"
)
PATH_PATTERN = re.compile(r"(^|\s)(~[/\\]|/[\w.-]+/|[A-Za-z]:\\)")


def normalize_text(text):
    """Apostroflarning turli shakllarini bitta ko'rinishga keltiradi (o‘ -> o')."""
    for char in APOSTROPHES:
        text = text.replace(char, "'")
    return text


def _tokens(text):
    return re.findall(r"[\w'+#]+", text.lower())


def parse_command(text):
    """'/kod ...' kabi buyruqni ajratadi. Buyruqdagi kichik xatolarni ham tushunadi."""
    stripped = text.lstrip()
    if not stripped.startswith("/"):
        return None, text
    head, _, rest = stripped[1:].partition(" ")
    if "\n" in head:
        head, _, extra = head.partition("\n")
        rest = extra + (" " + rest if rest else "")
    if not head or any(char in head for char in "/\\.~:"):
        return None, text  # Bu buyruq emas, fayl yo'li (masalan /home/user/...).
    name = normalize_text(head).lower()
    name = COMMAND_ALIASES.get(name, name)
    if name not in COMMANDS:
        match = difflib.get_close_matches(name, list(COMMANDS) + list(COMMAND_ALIASES), n=1, cutoff=0.7)
        if not match:
            return None, text
        name = COMMAND_ALIASES.get(match[0], match[0])
    return COMMANDS[name], rest.strip()


def _keyword_hit(keyword, text, tokens):
    if " " in keyword or not keyword.replace("'", "").isalnum():
        return keyword in text
    if keyword in tokens:
        return True
    if len(keyword) < 4:
        return False
    for token in tokens:
        # O'zbek tilida qo'shimchalar ko'p: "papkadagi", "faylimni" -> "papka", "fayl".
        if token.startswith(keyword) and len(token) - len(keyword) <= 7:
            return True
        if len(keyword) >= 5 and abs(len(token) - len(keyword)) <= 2 and token[0] == keyword[0]:
            if difflib.SequenceMatcher(None, token, keyword).ratio() >= 0.84:
                return True
    return False


def detect_skills(text, has_attachments=False, attachment_names=()):
    """Xabar mazmuniga qarab mos skill'larni tanlaydi (xatolarga chidamli)."""
    normalized = normalize_text(text).lower()
    tokens = set(_tokens(normalized)[:600])
    found = []
    for skill in SKILLS:
        if any(_keyword_hit(keyword, normalized, tokens) for keyword in skill.keywords):
            found.append(skill)
    if CODE_PATTERN.search(text) and SKILLS_BY_ID["code"] not in found:
        found.append(SKILLS_BY_ID["code"])
    if MATH_PATTERN.search(text) and SKILLS_BY_ID["math"] not in found:
        found.append(SKILLS_BY_ID["math"])
    if PATH_PATTERN.search(text) and SKILLS_BY_ID["files"] not in found:
        found.append(SKILLS_BY_ID["files"])
    table_suffixes = (".xlsx", ".xls", ".xlsm", ".csv", ".tsv", ".json")
    if any(str(name).lower().endswith(table_suffixes) for name in attachment_names):
        if SKILLS_BY_ID["data"] not in found:
            found.append(SKILLS_BY_ID["data"])
    # Bir xabarda juda ko'p skill bo'lsa, eng aniq uchtasi qoladi (tartib SKILLS bo'yicha).
    order = {skill.id: index for index, skill in enumerate(SKILLS)}
    found.sort(key=lambda skill: order[skill.id])
    return found[:3]


def select_skills(text, attachment_names=()):
    """Natija: (tanlangan skill'lar, modelga yuboriladigan matn)."""
    skill, rest = parse_command(text)
    if skill is not None:
        others = [item for item in detect_skills(rest, attachment_names=attachment_names) if item.id != skill.id]
        return [skill] + others[:1], rest
    return detect_skills(text, attachment_names=attachment_names), text


def public_skills():
    return [skill.public() for skill in SKILLS]
