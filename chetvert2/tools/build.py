"""Собирает chetvert2/src/main/assets/www/questions.js (сборник за 2 четверть).

questions_raw.json получен так:
  pdftotext по колонкам → python3 tools/parse_pdf_text.py cols.txt > questions_raw.json
Ключ ответов составлен вручную (в PDF его нет), разъяснения — в explanations/<предмет>.txt.

Формат ключа: один токен на вопрос по порядку.
  A/B/C/D — выбор ответа; 4321 — соответствие для A, B, C, D; =100 — ввод числа.
Рисунки вырезаются из PDF: python3 build.py <сборник.pdf>
(без аргумента используются уже лежащие в fig/).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WWW = os.path.join(HERE, "..", "src", "main", "assets", "www")
FRAME_W, FRAME_H = 820, 1160  # кадр страницы, в котором записаны координаты рисунков

KEY = {
    "russian": """B C A C C D C D C C  C D B D A B C C B B  C A C C B B C A B D
                  A D D D B B C D A B  C B C A C B A D 2345 3142 4521 1435 4125""",
    "literature": """B B A A B D C B A C  B B A C B D C C B A  B B C C B C B B B A
                     A C C B B B C C B B  B B C B A 2541 3415 2514 2431 2314""",
    "tajik": """A C B A C B A C A D  B B C D C C C B B D  B D C C C A D B A C
                D C B A D D D D C C  D B D C C B C C A D  D B A B C 2143 4321 4153 4532 2413""",
    "english": """A B D B C C D B C D  A C D C D B C D C C  D A B A B C B D A D
                  A D A A B A B A B C  3412 4321 4321 3421 2154 4321 2431 3512 4321 4325 2143""",
    "history_tj": """B D B A C C D B D B  A B D A A B C A A B  A C A A B B A A B D
                     B A A B A A C A A C  B A C A A 4321 5234 3421 2143 4213""",
    "history_general": """B C B B C D B B B C  A A D A B C A A A D  C C C C C C A A C C
                          D B B C B B B B B A  B A C C D B A D B C  D B B A C 4231 2134 1234 2143 2134""",
    "math": """C C B C A B B A A C  A A D C C C A D D B  D A A A D B C B B C
               C D D B B B B A B D  =50 =0 =4 =90 =38 =10 2413 1342 3152 5312 4132 2154""",
    "botany": """A C D D D D B C D B  C B D D A D A A B B  B D D C B D D A C A
                 C B B A D A B B B B  D D A C 3541 3251 5431 3125 3421 5421""",
    "it": """B C A B B C C B B B  B C D C B D C A D B  C D B 3152 2431 D B B B B
             A D A C A B A C B C  C 3241 2415 4231 B A B A A B  B C C B B B A B D C
             A C B C D B D B D D  C D A A 2413 1532 2514 1234""",
}

# Вопросы, ответ на которые стоит уточнить у учителя (номер по порядку).
UNSURE = {
    "russian": {9, 52, 53},
    "literature": {4, 8, 13, 29, 39, 48},
    "tajik": {28, 43, 56},
    "english": {47},
    "history_tj": {3, 4, 15, 19, 23, 28, 34, 39, 45, 48},
    "history_general": {6, 7, 13, 19, 59},
    "botany": {12, 23},
    "it": {15, 16, 29, 40, 46, 61},
}

LINE = {"wavy": "∼∼∼∼∼∼∼∼", "double": "═══════", "dash": "- - - - - - -", "solid": "________"}
ABCD = ["A", "B", "C", "D"]

# Форматирование, потерянное при извлечении текста: степени, подчёркивания, варианты-картинки.
FORMAT = {
    ("russian", 1): {"options": [LINE["wavy"], LINE["double"], LINE["dash"], LINE["solid"]]},
    ("russian", 6): {"options": [LINE["wavy"], LINE["double"], LINE["dash"], LINE["solid"]]},
    ("russian", 4): {"options": ["В нашем <u>лесу растут</u> разные <u>деревья</u>.",
                                 "<u>Свищет</u> ветер под крутым <u>забором</u>",
                                 "Бледно-серое <u>небо светлело</u>, <u>холодело</u>, <u>синело</u>.",
                                 "Сосны <u>росли</u> на песчаных <u>холмах</u>."]},
    ("russian", 8): {"text": "К какому падежу относятся падежные вопросы <i>кого? чего?</i>?"},
    ("russian", 10): {"text": "Какое слово в предложении <u><i>На краю опушки выросло маленькое деревце</i></u> образовано ПРИСТАВОЧНЫМ способом?"},
    ("russian", 12): {"text": "Укажите, какая характеристика выделенного в предложении слова неверна.\n<i>В лазури пламенной и чистой лениво тают <b>облака</b>.</i>"},
    ("russian", 13): {"text": "Какое вопросительное слово помогает определить безударные окончания имени прилагательного в данном предложении:\n<u>Ранним</u> утром приятно побродить по лесу."},
    ("russian", 14): {"text": "Какое вопросительное слово помогает определить безударные окончания имени прилагательного в данном предложении:\nБелка исчезла в <u>зеленой</u> хвое."},
    ("russian", 39): {"text": "К какому падежу относятся падежные вопросы <i>кому? чему?</i>?"},
    ("russian", 40): {"text": "К какому падежу относятся падежные вопросы <i>кого? что?</i>?"},
    ("russian", 41): {"text": "К какому падежу относятся падежные вопросы <i>кем? чем?</i>?"},
    ("russian", 42): {"text": "Какое вопросительное слово помогает определить безударные окончания имени прилагательного в данном предложении:\nГости собрались за <u>праздничным</u> столом."},
    ("literature", 17): {"text": "В сказке «Царевна-лягушка» есть предложение: <u><i>«Царь и все гости диву дались»</i></u>. Что означает подчёркнутое выражение:"},
    ("tajik", 33): {"options": ["ҳам-", "но-, бо-, бар-, бе-, ба-, то-", "бар-, во-, фар-, фур-", "на-, ме-, бо-"]},
    ("math", 1): {"text": "Найдите значение выражения: 5² + 2³"},
    ("math", 2): {"text": "Найдите значение выражения: 7 + 4³"},
    ("math", 8): {"options": ["560 см²", "280 дм²", "280 мм²", "280 см²"]},
    ("math", 10): {"text": "Найдите значение выражение:\n(15 − 7)² : 2³"},
    ("math", 11): {"options": ["8 дм", "36 дм 4 см", "364 дм²", "80 дм"]},
    ("math", 13): {"options": ["280 дм", "280 дм²", "280 мм²", "280 см²"]},
    ("math", 16): {"options": ["52 см²", "72 см³", "432 см³", "160 см"]},
    ("math", 18): {"text": "Вычислите: 5³ : (4² + 3²)."},
    ("math", 19): {"text": "Выполнить действия: 5 · 10³ + 2 · 10² + 6 · 10 + 4."},
    ("math", 21): {"options": ["46000 м²", "56789 м²", "2090 м²", "89600 м²"]},
    ("math", 22): {"options": ["37400 м²", "56789 м²", "2090 м²", "89600 м²"]},
    ("math", 23): {"options": ["7300 мм²; 392 мм", "730 мм²; 340 мм", "3920 мм²; 231 мм", "41456 мм²; 346 мм"]},
    ("math", 27): {"options": ["52 м²", "150 м²", "160 м³", "165 м³"]},
    ("math", 29): {"text": "Выразите 18 м² в дм²:", "options": ["180000 дм²", "1800 дм²", "180 дм²", "18000 дм²"]},
    ("math", 31): {"text": "Найдите сторону квадрата, если его площадь равна S = 81 см²."},
    ("math", 32): {"text": "С помощью формулы V = abc вычислите a, если V = 990 м³, b = 10 м, c = 11 м."},
    ("math", 36): {"text": "Одна из сторон прямоугольника равна 3 см, его площадь равна 18 см². Найдите вторую сторону прямоугольника."},
    ("math", 37): {"options": ["44 см³", "1331 см³", "2132 см³", "121 см³"]},
    ("math", 39): {"text": "Выразите 18 дм² в см²:", "options": ["180000 см²", "1800 см²", "180 см²", "1800 см"]},
    ("math", 45): {"text": "Вычислите. Напишите ответ.\n(12² + 2³) : 4"},
    ("math", 47): {"items": ["формула периметра прямоугольника", "формула площади квадрата", "формула скорости",
                             "формула объема куба", "периметр треугольника"],
                   "options": ["S = a²", "V = a³", "P = 2 · (a + b)", "V = S : t"]},
    ("math", 49): {"options": ["156 · x = 28080", "340 · y = 5780", "684 : p = 36", "729 : y = 27"]},
    ("math", 50): {"text": "Какие числа нужно подставить вместо x, чтобы получилось верное равенство?",
                   "options": ["2ˣ = 8", "2ˣ = 32", "3ˣ = 9", "3ˣ = 3"]},
    ("math", 51): {"items": ["32", "216 см³", "9 см", "15 м²", "5 м²"]},
    ("botany", 44): {"text": "Для прорастания семян <u><b>необязательным</b></u> условием является:"},
    ("botany", 5): {"text": "Между первым и вторым понятием в задании существует определенная связь. Такая же связь существует между третьим и одним из понятий, приведенных ниже. Найдите это понятие.\nХлоропласты : зелёные пластиды = наследственный аппарат клетки : ___________"},
    ("it", 7): {"options": ["‒", "=", "×", "нет правильного ответа"]},
    ("it", 25): {"options": ABCD},
    ("it", 43): {"options": ABCD},
    ("it", 44): {"options": ABCD, "items": ["Ярлыки и значки программ", "Панель задач", "Главное меню MS Windows",
                                            "Рабочий стол MS Windows", "Панель инструментов"]},
    ("it", 63): {"options": ["стиль текста", "тип шрифта", "размер текста", "печать"]},
    ("it", 66): {"options": ABCD},
    ("it", 69): {"text": "С помощью какой из этих кнопок можно изменить <u>цвет текста</u> в Microsoft Word?", "options": ABCD},
    ("it", 76): {"options": ABCD},
    ("it", 77): {"items": ["1", "2", "3", "4", "5"]},
}

# Рисунки: (страница, x, y, w, h) в кадре 820×1160; несколько кусков склеиваются по вертикали.
FIGURES = {
    ("it", 25): [(21, 445, 675, 110, 215)],
    ("it", 38): [(22, 485, 72, 260, 125)],
    ("it", 39): [(22, 485, 287, 260, 125)],
    ("it", 40): [(22, 485, 502, 260, 125)],
    ("it", 41): [(22, 485, 732, 260, 120)],
    ("it", 42): [(23, 68, 72, 260, 192)],
    ("it", 43): [(23, 52, 492, 360, 60), (23, 52, 552, 110, 68)],
    ("it", 44): [(23, 52, 742, 225, 320), (23, 445, 15, 160, 190)],
    ("it", 63): [(24, 522, 72, 170, 50)],
    ("it", 66): [(24, 445, 402, 80, 145)],
    ("it", 69): [(24, 445, 762, 80, 120)],
    ("it", 76): [(25, 52, 538, 130, 185)],
    ("it", 77): [(25, 445, 168, 80, 230)],
}


def clean(s):
    s = re.sub(r"\s+", " ", s.replace("\n", " / ")).strip()
    return s.replace(" / ", "\n")


def load_explanations(sid):
    res = {}
    for line in open(os.path.join(HERE, "explanations", sid + ".txt"), encoding="utf-8"):
        m = re.match(r"(\d+)\.\s+(.*)", line.strip())
        if m:
            res[int(m.group(1))] = m.group(2)
    return res


def crop_figures(pdf):
    from PIL import Image  # только при пересоздании рисунков

    os.makedirs(os.path.join(WWW, "fig"), exist_ok=True)
    pages = {}
    with tempfile.TemporaryDirectory() as tmp:
        for (sid, i), parts in FIGURES.items():
            crops = []
            for page, x, y, w, h in parts:
                if page not in pages:
                    out = os.path.join(tmp, f"p{page}")
                    subprocess.run(["pdftoppm", "-r", "200", "-png", "-singlefile", "-f", str(page), "-l", str(page),
                                    pdf, out], check=True)
                    pages[page] = Image.open(out + ".png").convert("RGB")
                im = pages[page]
                sx, sy = im.width / FRAME_W, im.height / FRAME_H
                crops.append(im.crop((int(x * sx), int(y * sy), int((x + w) * sx), int((y + h) * sy))))
            W = max(c.width for c in crops)
            sheet = Image.new("RGB", (W, sum(c.height for c in crops)), "white")
            y = 0
            for c in crops:
                sheet.paste(c, (0, y))
                y += c.height
            sheet.save(os.path.join(WWW, "fig", f"{sid}{i}.png"), optimize=True)


def main():
    if len(sys.argv) == 2:
        crop_figures(sys.argv[1])
    raw = json.load(open(os.path.join(HERE, "questions_raw.json"), encoding="utf-8"))
    out = []
    for subj in raw:
        sid = subj["id"]
        keys, qs, expl = KEY[sid].split(), subj["questions"], load_explanations(sid)
        assert len(keys) == len(qs), (sid, len(keys), len(qs))
        res = []
        for i, (q, k) in enumerate(zip(qs, keys), start=1):
            q = dict(q, **FORMAT.get((sid, i), {}))
            item = {"n": i, "label": q["n"], "text": clean(q["text"])}
            if (sid, i) in FIGURES:
                item["figure"] = f'<img class="fig" src="fig/{sid}{i}.png" alt="Рисунок к заданию">'
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
                assert len(q["options"]) == 4 and k in "ABCD", (sid, i, k, q["options"])
                item["type"] = "choice"
                item["options"] = [clean(o) for o in q["options"]]
                item["answer"] = "ABCD".index(k)
            assert i in expl, (sid, i, "нет пояснения")
            item["explain"] = expl[i]
            if i in UNSURE.get(sid, ()):
                item["unsure"] = True
            res.append(item)
        out.append({"id": sid, "title": subj["title"], "questions": res})
        print(f"{sid:16} {len(res)} вопросов")
    with open(os.path.join(WWW, "questions.js"), "w", encoding="utf-8") as f:
        f.write("// Сгенерировано chetvert2/tools/build.py — не редактировать вручную.\n")
        f.write("window.SUBJECTS = ")
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write(";\n")


if __name__ == "__main__":
    main()
