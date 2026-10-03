import pytest

from localai.skills import detect_skills, normalize_text, parse_command, select_skills


def ids(skills):
    return [skill.id for skill in skills]


def test_parse_command():
    skill, rest = parse_command("/kod salom dunyo yoz")
    assert skill.id == "code" and rest == "salom dunyo yoz"
    skill, rest = parse_command("/tarjma inglizchaga: salom")
    assert skill.id == "translate" and rest == "inglizchaga: salom"
    skill, rest = parse_command("/imlo\nbirinchi qator")
    assert skill.id == "spelling" and rest == "birinchi qator"
    assert parse_command("/home/user/project papkasini ko'r")[0] is None
    assert parse_command("/qwertyuiop")[0] is None
    assert parse_command("oddiy xabar")[0] is None


@pytest.mark.parametrize("text, expected", [
    ("pyton da list sortlash kodini yozb ber", "code"),
    ("Traceback (most recent call last):\n  File x", "code"),
    ("Desktop papkadagi fayllarni ko'rib chiq", "files"),
    ("~/projects/app ni tahlil qil", "files"),
    ("matnimni imlosini tekshir, xatolarini tuzat", "spelling"),
    ("buni inglizchaga tarjima qil", "translate"),
    ("12 500 000 * 12% qancha bo'ladi", "math"),
    ("excel jadvaldagi savdoni tahlil qil", "data"),
    ("bu maqolaning qisqacha mazmunini yoz", "summary"),
])
def test_detect_skills_with_typos(text, expected):
    assert expected in ids(detect_skills(text))


def test_attachment_activates_data_skill():
    assert "data" in ids(detect_skills("ko'rib chiq", attachment_names=["hisobot.xlsx"]))


def test_plain_greeting_has_no_skills():
    assert detect_skills("salom, qalaysan?") == []
    assert "files" not in ids(detect_skills("kvant kompyuter nima?"))


def test_select_skills_strips_command():
    skills, body = select_skills("/xulosa bu matn juda uzun")
    assert ids(skills)[0] == "summary" and body == "bu matn juda uzun"


def test_normalize_apostrophes():
    assert normalize_text("o‘zbek g’alaba ma`lumot") == "o'zbek g'alaba ma'lumot"
