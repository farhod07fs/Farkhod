"""Разбор текста, извлечённого из PDF (pdftotext по колонкам), в JSON с вопросами.

Использование: python3 parse_pdf_text.py cols.txt > questions_raw.json
Ответы в PDF отсутствуют — они добавляются отдельно (tools/answers.py).
"""
import json
import re
import sys

SUBJECTS = [
    ("РУССКИЙ ЯЗЫК", "russian", "Русский язык"),
    ("РУССКАЯ ЛИТЕРАТУРА", "literature", "Русская литература"),
    ("ЗАБОНИ ДАВЛАТ", "tajik", "Забони давлатӣ"),
    ("АНГЛИЙСКИЙ ЯЗЫК", "english", "Английский язык"),
    ("БОТАНИКА", "botany", "Ботаника"),
    ("ИСТОРИЯ ТАДЖИКСКОГО НАРОДА", "history_tj", "История таджикского народа"),
    ("ИСТОРИЯ ДРЕВНЕГО МИРА", "history_ancient", "История древнего мира"),
    ("МАТЕМАТИКА", "math", "Математика"),
    ("ИНФОРМАЦИОННАЯ ТЕХНОЛОГИЯ", "it", "Информационная технология"),
]

SKIP = re.compile(r"^(=====.*|\d{1,2}|1 четверть|чоряки 1|Column [AB]|РАЗДЕЛ .*|Единицы измерения информации)$")
Q_RE = re.compile(r"^(\d{1,2})\s*\.\s*(.*)$")
OPT_RE = re.compile(r"^([АAВBСCD])\s*\)\s*(.*)$")
NUM_RE = re.compile(r"^([1-5])\s*\)\s*(.*)$")

# Таджикские буквы в PDF набраны старым шрифтом — заменяем на Unicode.
TJ_FIX = str.maketrans({"Ї": "Ӣ", "ї": "ӣ", "Ў": "Ӯ", "ў": "ӯ", "Ќ": "Қ", "ќ": "қ",
                        "Њ": "Ҳ", "њ": "ҳ", "Ѓ": "Ғ", "ѓ": "ғ", "Љ": "Ҷ", "љ": "ҷ"})


def main(path):
    lines = [l.strip() for l in open(path, encoding="utf-8")]
    subjects, subj, q = [], None, None

    def flush():
        if q is not None:
            subj["questions"].append(q)

    for line in lines:
        if not line or SKIP.match(line):
            continue
        head = next((s for s in SUBJECTS if line.startswith(s[0]) and "класс" in line), None)
        if head:
            flush()
            q = None
            subj = {"id": head[1], "title": head[2], "questions": []}
            subjects.append(subj)
            continue
        m = Q_RE.match(line)
        if m and not (q and not q["options"] and not q["items"] and q["text"].endswith(":") and False):
            flush()
            q = {"n": int(m.group(1)), "text": m.group(2), "options": [], "items": []}
            continue
        m = OPT_RE.match(line)
        if m and q is not None:
            q["options"].append(m.group(2))
            continue
        m = NUM_RE.match(line)
        if m and q is not None:
            q["items"].append(m.group(2))
            continue
        # продолжение предыдущей строки
        if q["items"] and (q["options"] and len(q["items"]) > 0):
            q["items"][-1] += " " + line
        elif q["options"]:
            q["options"][-1] += " " + line
        elif q["items"]:
            q["items"][-1] += " " + line
        else:
            q["text"] += ("\n" if q["text"].endswith((":", "?", ".")) else " ") + line
    flush()
    for s in subjects:
        if s["id"] == "tajik":
            for q in s["questions"]:
                q["text"] = q["text"].translate(TJ_FIX)
                q["options"] = [o.translate(TJ_FIX) for o in q["options"]]
                q["items"] = [o.translate(TJ_FIX) for o in q["items"]]
    json.dump(subjects, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
