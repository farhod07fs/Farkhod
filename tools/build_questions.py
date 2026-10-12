"""Собирает app/src/main/assets/www/questions.js из questions_raw.json и ключа ответов.

Формат ключа: один токен на вопрос по порядку.
  A/B/C/D         — вопрос с выбором ответа;
  4321            — соответствие: цифры для пунктов A, B, C, D;
  =100 / =18|22   — вопрос с вводом ответа (через | — допустимые варианты).
Номера в UNSURE — вопросы, где ответ спорный (ключа в PDF нет).
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "app", "src", "main", "assets", "www", "questions.js")

KEY = {
    "russian": """B D C C A A C A D C  C D D D C D D C C C  D C C A B A D B C C
                  C B D B B C B B D B  D D A C C 4321 4213 3142 4531 3514""",
    "literature": """B A A A A B B B C A  A B B B B D D C B B  A B D C C B B C A B
                     C C B C B A B D B A  B D A A D A 5124 3524 4152 5421 3152""",
    "tajik": """C A B C C D C D C A  B B A D B B C B D D  D A D A B C B C A D
                A B C D A A C D C B  B C A C A A A B A A  C A D C A C 4531 3412 2413 3124""",
    "english": """C B B A D A A A B D  D A B D A C C D A B  C B D A C D A C D B
                  C A B C B C D B D C  B D 4123 5124 4321 4321 3214 2431 3412 5412 5132 5423""",
    "botany": """C D A A B B C D B B  D B A A D D D B B B  B D C C D A B C D B
                 B A B B A D B A C B  3451 2315 5312 2351 3215 4312 2543 3412 5312 1423""",
    "history_tj": """A A A A A C A A B A  A A C A A C A C D C  C C B C A B A D A D
                     A C B D B C D A A A  A A A A A 1324 3214 1345 4312 4231""",
    "history_ancient": """A A A A A A A B D A  A C D B A B A C A C  B C C D C C C D A C
                          C C A A A A A A A A  A C A A A C 1324 4321 4215 4513 1234""",
    "math": """D A C B A B A B D A  C B B C B C A D D B  B C C B B D B B B C
               A B B B A D D D D D  =100 =18|22 =24 =7 =3920 4213 2453 3142 2315 5314 3124""",
    "it": """A B B A B D C A C C  D C B D C A A B C D  C B B B B C D B B A
             D C B C B C D 1423 5241 B  C B C A C C C C B A  B B B D B B D B A B
             A B B C D 1234 2143 2413 2315""",
}

# Вопросы, ответ на которые стоит проверить учителю.
UNSURE = {
    "russian": {16, 37, 44},
    "literature": {8, 16, 28, 45},
    "tajik": {15, 33, 44, 46, 50},
    "botany": {6, 13, 15},
    "history_tj": {4, 5, 7, 10, 15, 26, 28, 31, 38, 48, 49},
    "history_ancient": {2, 24, 38, 47},
    "math": {42},
    "it": {9, 54, 62},
}

LINES_SVG = """<svg viewBox="0 0 300 200" class="fig" role="img" aria-label="Рисунок к заданию">
<g stroke="currentColor" stroke-width="3" fill="currentColor" font-size="14" font-family="sans-serif">
<text x="0" y="40" stroke="none">1)</text><text x="40" y="22" stroke="none">A</text><text x="270" y="22" stroke="none">B</text><line x1="40" y1="35" x2="290" y2="35"/>
<text x="0" y="85" stroke="none">2)</text><text x="40" y="67" stroke="none">O</text><text x="270" y="67" stroke="none">B</text><line x1="40" y1="80" x2="290" y2="80"/><circle cx="40" cy="80" r="5"/>
<text x="0" y="130" stroke="none">3)</text><text x="40" y="112" stroke="none">A</text><text x="270" y="112" stroke="none">B</text><line x1="40" y1="125" x2="280" y2="125"/><circle cx="40" cy="125" r="5"/><circle cx="280" cy="125" r="5"/>
<text x="0" y="175" stroke="none">4)</text><text x="40" y="157" stroke="none">Д</text><text x="270" y="157" stroke="none">М</text><line x1="40" y1="170" x2="280" y2="170"/><circle cx="280" cy="170" r="5"/>
</g></svg>"""

# Исправления текста, который в PDF был рисунком или потерял форматирование.
FIX = {
    ("botany", 16): {"text": "Совокупность растений определённой территории называется:"},
    ("literature", 31): {"text": "В сказке «Царевна-лягушка» есть предложение: «Царь и все гости <u>диву дались</u>». Что означает подчёркнутое выражение:"},
    ("math", 3): {"text": "Чему равен отрезок CB, если AB = 28 см, а AC = 19 см? (точка C лежит на отрезке AB)"},
    ("math", 16): {"text": "Чему равен отрезок AC, если AB = 24 см и BC = 8 см? (точка C лежит на отрезке AB)"},
    ("math", 27): {"text": "На рисунке изображён отрезок AB, точка C лежит на нём. Если AB = 44 см и BC = 14 см, то чему равен отрезок AC?"},
    ("math", 7): {"text": "Укажите отрезок, луч и прямую линию.", "figure": LINES_SVG, "items": []},
    ("math", 11): {"text": "Найдите периметр прямоугольника, если длина a = 12 см и ширина b = 8 см."},
    ("math", 14): {"text": "Найдите периметр прямоугольника, если длина a = 14 см и ширина b = 7 см."},
    ("math", 22): {"text": "Дан квадрат со стороной 12 см и прямоугольник со сторонами 8 см и 40 см. Найдите сумму площадей квадрата и прямоугольника.",
                   "options": ["200 см³", "144 см²", "464 см²", "1040 см²"]},
    ("math", 23): {"text": "Дан квадрат со стороной 13 см и прямоугольник со сторонами 11 см и 20 см. Найдите сумму площадей квадрата и прямоугольника.",
                   "options": ["200 см³", "144 см²", "389 см²", "1040 см²"]},
    ("math", 32): {"text": "Решить уравнение: (x + 15) – 8 = 17"},
    ("math", 50): {"options": ["P = 2 · (a + b)", "S = a²", "P = 4 · a", "S = a · b"]},
    ("math", 51): {"options": ["2 · 3² + 10", "3 · 2³ + 5²", "2 · 3² + 3 · 4³", "2² · 3²"]},
}


def clean(s):
    s = re.sub(r"\s+", " ", s.replace("\n", " / ")).strip()
    return s.replace(" / ", "\n")


def main():
    raw = json.load(open(os.path.join(HERE, "questions_raw.json"), encoding="utf-8"))
    out = []
    for subj in raw:
        sid = subj["id"]
        keys = KEY[sid].split()
        qs = subj["questions"]
        assert len(keys) == len(qs), (sid, len(keys), len(qs))
        res = []
        for i, (q, k) in enumerate(zip(qs, keys), start=1):
            q = dict(q, **FIX.get((sid, i), {}))
            item = {"n": i, "text": clean(q["text"])}
            if q.get("figure"):
                item["figure"] = q["figure"]
            if k.startswith("="):
                assert not q["options"], (sid, i)
                item["type"] = "input"
                item["answer"] = k[1:].split("|")
            elif k.isdigit():
                assert len(k) == 4 and len(q["options"]) == 4 and len(q["items"]) == 5, (sid, i)
                item["type"] = "match"
                item["left"] = [clean(o) for o in q["options"]]
                item["right"] = [clean(o) for o in q["items"]]
                item["answer"] = [int(c) - 1 for c in k]
            else:
                assert len(q["options"]) == 4 and k in "ABCD", (sid, i, k)
                item["type"] = "choice"
                if q["items"]:  # пронумерованные условия внутри вопроса (математика)
                    item["text"] += "\n" + "\n".join(f"{j}) {clean(t)}" for j, t in enumerate(q["items"], 1))
                item["options"] = [clean(o) for o in q["options"]]
                item["answer"] = "ABCD".index(k)
            if i in UNSURE.get(sid, ()):
                item["unsure"] = True
            res.append(item)
        out.append({"id": sid, "title": subj["title"], "questions": res})
        print(f"{sid:16} {len(res)} вопросов")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Сгенерировано tools/build_questions.py — не редактировать вручную.\n")
        f.write("window.SUBJECTS = ")
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write(";\n")


if __name__ == "__main__":
    main()
