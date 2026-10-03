"""Xavfsiz kalkulyator: faqat matematik ifodalar, hech qanday kod bajarilmaydi."""

import ast
import math
import operator
import re
import statistics


BINARY = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf}


def _factorial(value):
    if value != int(value) or value < 0 or value > 1000:
        raise ValueError("factorial faqat 0..1000 butun sonlar uchun")
    return math.factorial(int(value))


def _percent(value, total):
    return value * total / 100


FUNCTIONS = {
    "sqrt": math.sqrt, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x), "abs": abs,
    "round": round, "floor": math.floor, "ceil": math.ceil, "exp": math.exp,
    "log": math.log, "ln": math.log, "log10": math.log10, "log2": math.log2,
    "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin, "acos": math.acos,
    "atan": math.atan, "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "degrees": math.degrees, "radians": math.radians, "factorial": _factorial,
    "gcd": math.gcd, "lcm": math.lcm, "min": min, "max": max, "sum": lambda *a: sum(_flat(a)),
    "mean": lambda *a: statistics.fmean(_flat(a)), "avg": lambda *a: statistics.fmean(_flat(a)),
    "median": lambda *a: statistics.median(_flat(a)), "hypot": math.hypot,
    "comb": math.comb, "perm": math.perm, "percent": _percent, "pow": pow,
}


def _flat(values):
    flat = []
    for value in values:
        if isinstance(value, (list, tuple)):
            flat.extend(value)
        else:
            flat.append(value)
    return flat


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.Name) and node.id.lower() in CONSTANTS:
        return CONSTANTS[node.id.lower()]
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow):
            if abs(right) > 1000 or (abs(left) > 1e6 and abs(right) > 50):
                raise ValueError("daraja juda katta")
        return BINARY[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        return UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(item) for item in node.elts]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        name = node.func.id.lower()
        if name in FUNCTIONS:
            return FUNCTIONS[name](*[_eval(arg) for arg in node.args])
    raise ValueError("ruxsat etilmagan ifoda")


def normalize(expression):
    text = str(expression).strip()
    text = text.replace("×", "*").replace("·", "*").replace("÷", "/").replace("−", "-")
    text = text.replace("^", "**").replace("√", "sqrt")
    text = re.sub(r"(\d)\s+(?=\d{3}\b)", r"\1", text)  # 1 000 000 -> 1000000
    text = re.sub(r"(\d+(?:\.\d+)?)\s*%\s*(?:of|dan|from)\s*(\d+(?:\.\d+)?)", r"percent(\1, \2)", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", text)
    return text


def format_number(value):
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ") if abs(value) >= 10000 else str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return str(value)
        if value.is_integer() and abs(value) < 1e15:
            return format_number(int(value))
        return f"{value:.12g}"
    if isinstance(value, list):
        return "[" + ", ".join(format_number(item) for item in value) + "]"
    return str(value)


def calculate(expression):
    text = normalize(expression)
    if len(text) > 500:
        raise ValueError("ifoda juda uzun")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as error:
        raise ValueError("ifodani tushunib bo'lmadi") from error
    try:
        value = _eval(tree)
    except ZeroDivisionError as error:
        raise ValueError("nolga bo'lish mumkin emas") from error
    except OverflowError as error:
        raise ValueError("natija juda katta") from error
    except (TypeError, ValueError) as error:
        raise ValueError(str(error) or "noto'g'ri ifoda") from error
    return format_number(value)
