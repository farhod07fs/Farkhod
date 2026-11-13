"""Собирает vilenkin/src/main/assets/www/questions.js и рисунки из tests.txt.

tests.txt — вопросы, переписанные со скана сборника, key.txt — официальный ключ.
Каждый ответ «= N» сверяется с ключом; расхождение допускается только из списка
KEY_OVERRIDES (там, где в ключе сборника опечатка).

Рисунки вырезаются из скана: python3 build.py <скан A.pdf> <скан B.pdf>
Без аргументов рисунки не пересоздаются (используются уже лежащие в fig/).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WWW = os.path.join(HERE, "..", "src", "main", "assets", "www")
FRAME_W, FRAME_H = 620, 915  # кадр, в котором записаны координаты рисунков

# (тест, вариант, вопрос) -> ответ, отличающийся от ключа сборника
KEY_OVERRIDES = {(16, 1, 6): 1, (14, 2, 3): 3}


def parse_key():
    key = {}
    for line in open(os.path.join(HERE, "key.txt"), encoding="utf-8"):
        m = re.match(r"(\d+):(.*)\|(.*)", line)
        if m:
            key[int(m.group(1))] = [list(map(int, m.group(2).split())), list(map(int, m.group(3).split()))]
    return key


def parse_tests():
    tests, test, var, q = [], None, None, None
    for raw in open(os.path.join(HERE, "tests.txt"), encoding="utf-8"):
        line = raw.rstrip("\n")
        if line.startswith("# T"):
            m = re.match(r"# T(\d+) \| (.*)", line)
            test = {"n": int(m.group(1)), "title": m.group(2).strip(), "variants": []}
            tests.append(test)
            q = None
        elif line.startswith("## "):
            var = []
            test["variants"].append(var)
            q = None
        elif line.startswith("#") or test is None:
            continue
        elif re.match(r"^\d+\. ", line):
            n, text = line.split(". ", 1)
            q = {"n": int(n), "text": text, "options": []}
            var.append(q)
        elif q is None or not line.strip():
            continue
        elif line.startswith("- "):
            q["options"].append(line[2:])
        elif line.startswith("= "):
            q["answer"] = int(line[2:]) - 1
        elif line.startswith("? "):
            q["explain"] = line[2:]
        elif line.startswith("! "):
            q["note"] = line[2:]
        elif line.startswith("@ "):
            f, page, x, y, w, h = line[2:].split()
            q["fig"] = (f, int(page), int(x), int(y), int(w), int(h))
        elif not q["options"]:
            q["text"] += "\n" + line
        else:
            raise SystemExit(f"Непонятная строка: {line!r}")
    return tests


def crop_figures(tests, scans):
    from PIL import Image  # только при пересоздании рисунков

    os.makedirs(os.path.join(WWW, "fig"), exist_ok=True)
    need = {}
    for t in tests:
        for vi, var in enumerate(t["variants"], 1):
            for q in var:
                if "fig" in q:
                    need.setdefault((q["fig"][0], q["fig"][1]), []).append((t["n"], vi, q))
    with tempfile.TemporaryDirectory() as tmp:
        for (f, page), items in sorted(need.items()):
            out = os.path.join(tmp, f"{f}{page}")
            subprocess.run(["pdftoppm", "-r", "200", "-png", "-singlefile", "-f", str(page), "-l", str(page),
                            scans[f], out], check=True)
            im = Image.open(out + ".png").convert("L")
            sx, sy = im.width / FRAME_W, im.height / FRAME_H
            for tn, vi, q in items:
                _, _, x, y, w, h = q["fig"]
                crop = im.crop((int(x * sx), int(y * sy), int((x + w) * sx), int((y + h) * sy)))
                crop.save(os.path.join(WWW, "fig", f"t{tn}v{vi}q{q['n']}.png"), optimize=True)


def main():
    tests, key = parse_tests(), parse_key()
    if len(sys.argv) == 3:
        crop_figures(tests, {"A": sys.argv[1], "B": sys.argv[2]})
    errors, out, total = [], [], 0
    for t in tests:
        ks = key[t["n"]]
        assert len(t["variants"]) == 2, t["n"]
        variants = []
        for vi, var in enumerate(t["variants"], 1):
            if len(var) != len(ks[vi - 1]):
                errors.append(f"Т{t['n']} В{vi}: {len(var)} вопросов, в ключе {len(ks[vi - 1])}")
            items = []
            for i, q in enumerate(var, 1):
                where = f"Т{t['n']} В{vi} №{q['n']}"
                if q["n"] != i:
                    errors.append(f"{where}: ожидался номер {i}")
                if "answer" not in q or "explain" not in q or len(q["options"]) < 2:
                    errors.append(f"{where}: нет ответа, разъяснения или вариантов")
                    continue
                official = ks[vi - 1][i - 1] - 1 if i <= len(ks[vi - 1]) else None
                expected = KEY_OVERRIDES.get((t["n"], vi, i), official + 1 if official is not None else None)
                if q["answer"] + 1 != expected:
                    errors.append(f"{where}: ответ {q['answer'] + 1}, в ключе {official + 1}")
                if not 0 <= q["answer"] < len(q["options"]):
                    errors.append(f"{where}: ответ вне вариантов")
                item = {"n": i, "text": q["text"], "options": q["options"], "answer": q["answer"],
                        "explain": q["explain"]}
                if "fig" in q:
                    item["fig"] = f"fig/t{t['n']}v{vi}q{i}.png"
                if "note" in q:
                    item["note"] = q["note"]
                items.append(item)
                total += 1
            variants.append(items)
        out.append({"id": f"t{t['n']}", "n": t["n"], "title": t["title"], "variants": variants})
    if errors:
        raise SystemExit("Ошибки:\n" + "\n".join(errors))
    with open(os.path.join(WWW, "questions.js"), "w", encoding="utf-8") as f:
        f.write("// Сгенерировано vilenkin/tools/build.py — не редактировать вручную.\n")
        f.write("window.TESTS = ")
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write(";\n")
    print(f"тестов: {len(out)}, вопросов: {total}")


if __name__ == "__main__":
    main()
