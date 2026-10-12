(function () {
  "use strict";

  var SUBJECTS = window.SUBJECTS || [];
  var LETTERS = ["A", "B", "C", "D"];
  var ICONS = {
    russian: "📘", literature: "📖", tajik: "🇹🇯", english: "🇬🇧", botany: "🌱",
    history_tj: "🏺", history_ancient: "🏛️", math: "➗", it: "💻"
  };
  var RANDOM_COUNT = 20;

  var view = document.getElementById("view");
  var titleEl = document.getElementById("title");
  var counterEl = document.getElementById("counter");
  var backBtn = document.getElementById("back");
  var progressBar = document.querySelector("#progress div");

  var quiz = null; // текущая попытка

  // ---------- хранилище ----------
  function load(key, def) {
    try { var v = localStorage.getItem(key); return v ? JSON.parse(v) : def; } catch (e) { return def; }
  }
  function save(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) { /* без сохранения */ }
  }
  function mistakesOf(sid) { return load("mistakes:" + sid, []); }
  function bestOf(sid) { return load("best:" + sid, null); }

  // ---------- утилиты ----------
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    }).replace(/&lt;(\/?)u&gt;/g, "<$1u>");
  }
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function shuffle(a) {
    a = a.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function subject(sid) {
    for (var i = 0; i < SUBJECTS.length; i++) if (SUBJECTS[i].id === sid) return SUBJECTS[i];
    return null;
  }
  function grade(pct) {
    if (pct >= 85) return "5 — отлично!";
    if (pct >= 70) return "4 — хорошо";
    if (pct >= 50) return "3 — удовлетворительно";
    return "2 — нужно повторить";
  }
  function header(title, counter, canBack) {
    titleEl.textContent = title;
    counterEl.textContent = counter || "";
    backBtn.hidden = !canBack;
    if (!quiz) progressBar.style.width = "0";
    window.scrollTo(0, 0);
  }
  function normalize(s) { return String(s).replace(/\s+/g, "").replace(",", ".").toLowerCase(); }

  // ---------- навигация (через hash, чтобы работала кнопка «Назад» Android) ----------
  function go(hash) { if (location.hash === hash) route(); else location.hash = hash; }
  backBtn.onclick = function () { history.back(); };
  window.addEventListener("hashchange", route);

  function route() {
    var h = location.hash.replace(/^#\/?/, "").split("/");
    if (h[0] === "s" && subject(h[1])) {
      quiz = null;
      return showSubject(subject(h[1]));
    }
    if (h[0] === "q" && quiz) return showQuestion();
    if (h[0] === "r" && quiz) return showResult();
    quiz = null;
    showHome();
  }

  // ---------- экраны ----------
  function showHome() {
    header("Тесты · 5 класс · 1 четверть", "", false);
    view.innerHTML = "";
    var total = SUBJECTS.reduce(function (n, s) { return n + s.questions.length; }, 0);
    view.appendChild(el("p", "muted", "Выберите предмет. Всего вопросов: " + total + "."));
    var list = el("div", "subjects");
    SUBJECTS.forEach(function (s) {
      var b = el("button", "subject");
      var best = bestOf(s.id);
      b.innerHTML = '<span class="emoji">' + (ICONS[s.id] || "📝") + "</span>" +
        '<span><div class="name">' + esc(s.title) + '</div><div class="meta">' + s.questions.length + " вопросов</div></span>" +
        (best != null ? '<span class="best">' + best + "%</span>" : "");
      b.onclick = function () { go("#/s/" + s.id); };
      list.appendChild(b);
    });
    view.appendChild(list);
    view.appendChild(el("p", "muted",
      "Ответы составлены по учебной программе, так как в исходном файле ключа нет. " +
      "Вопросы с пометкой «⚠» лучше уточнить у учителя."));
  }

  function showSubject(s) {
    header(s.title, "", true);
    view.innerHTML = "";
    var n = s.questions.length;
    var mistakes = mistakesOf(s.id);
    var best = bestOf(s.id);
    var info = el("div", "card");
    info.innerHTML = "<div>" + (ICONS[s.id] || "") + " <b>" + esc(s.title) + "</b></div>" +
      '<div class="muted">' + n + " вопросов" + (best != null ? " · лучший результат " + best + "%" : "") + "</div>";
    view.appendChild(info);

    function modeBtn(label, sub, ids, primary) {
      var b = el("button", "btn" + (primary ? " primary" : ""), esc(label) + "<small>" + esc(sub) + "</small>");
      b.disabled = !ids.length;
      b.onclick = function () { start(s, ids); };
      view.appendChild(b);
    }
    var all = s.questions.map(function (q) { return q.n; });
    modeBtn("Случайные " + Math.min(RANDOM_COUNT, n) + " вопросов", "быстрая проверка", shuffle(all).slice(0, RANDOM_COUNT), true);
    modeBtn("Все вопросы по порядку", "1 – " + n, all);
    modeBtn("Все вопросы вперемешку", n + " вопросов в случайном порядке", shuffle(all));
    modeBtn("Работа над ошибками", mistakes.length ? mistakes.length + " вопросов, где были ошибки" : "ошибок пока нет", mistakes.slice());
  }

  function start(s, ids) {
    var byN = {};
    s.questions.forEach(function (q) { byN[q.n] = q; });
    quiz = { subject: s, list: ids.map(function (n) { return byN[n]; }).filter(Boolean), pos: 0, correct: 0, wrong: [], answered: false };
    // С экрана предмета — новая запись в истории (Назад вернёт к выбору режима),
    // с экрана результата — замена, чтобы не копить историю.
    if (location.hash.indexOf("#/s/") === 0) go("#/q");
    else location.replace("#/q");
  }

  function showQuestion() {
    var q = quiz.list[quiz.pos];
    var s = quiz.subject;
    quiz.answered = false;
    header(s.title, (quiz.pos + 1) + " / " + quiz.list.length, true);
    progressBar.style.width = (quiz.pos / quiz.list.length * 100) + "%";
    view.innerHTML = "";

    var card = el("div", "card");
    card.appendChild(el("div", "qnum", "Вопрос № " + q.n + (q.unsure ? " ⚠" : "")));
    card.appendChild(el("p", "qtext", esc(q.text)));
    if (q.figure) card.insertAdjacentHTML("beforeend", q.figure);
    view.appendChild(card);

    var area = el("div");
    view.appendChild(area);
    var feedback = el("div");
    view.appendChild(feedback);

    if (q.type === "choice") renderChoice(q, area, feedback);
    else if (q.type === "match") renderMatch(q, area, feedback, card);
    else renderInput(q, area, feedback);
  }

  function finish(q, ok, yourText, rightText, feedback) {
    quiz.answered = true;
    if (ok) quiz.correct++;
    else quiz.wrong.push({ q: q, your: yourText, right: rightText });

    var mistakes = mistakesOf(quiz.subject.id).filter(function (n) { return n !== q.n; });
    if (!ok) mistakes.push(q.n);
    save("mistakes:" + quiz.subject.id, mistakes);

    feedback.innerHTML = "";
    feedback.appendChild(el("p", "feedback " + (ok ? "ok" : "bad"),
      ok ? "✔ Верно!" : "✘ Неверно. Правильный ответ: " + esc(rightText)));
    if (q.unsure) feedback.appendChild(el("p", "note", "⚠ Ответ на этот вопрос лучше уточнить у учителя."));
    var last = quiz.pos === quiz.list.length - 1;
    var next = el("button", "btn primary", last ? "Показать результат" : "Следующий вопрос →");
    next.onclick = nextQuestion;
    feedback.appendChild(next);
    next.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function nextQuestion() {
    if (quiz.pos < quiz.list.length - 1) {
      quiz.pos++;
      showQuestion();
    } else {
      location.replace("#/r");
    }
  }

  function renderChoice(q, area, feedback) {
    var buttons = q.options.map(function (text, i) {
      var b = el("button", "btn opt", '<span class="letter">' + LETTERS[i] + "</span><span>" + esc(text) + "</span>");
      b.onclick = function () {
        if (quiz.answered) return;
        var ok = i === q.answer;
        buttons[q.answer].classList.add("ok");
        if (!ok) b.classList.add("bad");
        finish(q, ok, LETTERS[i] + ") " + text, LETTERS[q.answer] + ") " + q.options[q.answer], feedback);
      };
      area.appendChild(b);
      return b;
    });
  }

  function renderMatch(q, area, feedback, card) {
    var ul = el("ul", "match-right");
    q.right.forEach(function (t, i) { ul.appendChild(el("li", "", "<b>" + (i + 1) + ")</b> " + esc(t))); });
    card.appendChild(ul);
    card.appendChild(el("div", "muted", "Для каждого пункта A–D выберите номер из списка выше."));

    var chosen = [null, null, null, null];
    var rows = q.left.map(function (t, li) {
      var row = el("div", "mrow");
      row.appendChild(el("div", "lbl", "<b>" + LETTERS[li] + ")</b> " + esc(t)));
      var nums = el("div", "nums");
      var btns = [0, 1, 2, 3, 4].map(function (ri) {
        var b = el("button", "", String(ri + 1));
        b.onclick = function () {
          if (quiz.answered) return;
          chosen[li] = ri;
          btns.forEach(function (x, k) { x.classList.toggle("sel", k === ri); });
          check.disabled = chosen.indexOf(null) !== -1;
        };
        nums.appendChild(b);
        return b;
      });
      row.appendChild(nums);
      area.appendChild(row);
      return btns;
    });
    var check = el("button", "btn primary", "Проверить");
    check.disabled = true;
    check.onclick = function () {
      if (quiz.answered) return;
      check.remove();
      var ok = true;
      rows.forEach(function (btns, li) {
        var right = q.answer[li];
        btns.forEach(function (b) { b.classList.remove("sel"); });
        btns[right].classList.add("ok");
        if (chosen[li] !== right) { ok = false; btns[chosen[li]].classList.add("bad"); }
      });
      var fmt = function (arr) { return arr.map(function (r, i) { return LETTERS[i] + "–" + (r + 1); }).join(", "); };
      finish(q, ok, fmt(chosen), fmt(q.answer), feedback);
    };
    area.appendChild(check);
  }

  function renderInput(q, area, feedback) {
    var input = el("input", "answer");
    input.type = "text";
    input.inputMode = "numeric";
    input.placeholder = "Ваш ответ";
    area.appendChild(input);
    var check = el("button", "btn primary", "Проверить");
    function submit() {
      if (quiz.answered || !input.value.trim()) return;
      var ok = q.answer.some(function (a) { return normalize(a) === normalize(input.value); });
      input.classList.add(ok ? "ok" : "bad");
      input.disabled = true;
      check.remove();
      finish(q, ok, input.value.trim(), q.answer[0], feedback);
    }
    check.onclick = submit;
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") submit(); });
    area.appendChild(check);
    setTimeout(function () { input.focus(); }, 50);
  }

  function showResult() {
    var s = quiz.subject;
    var total = quiz.list.length;
    var pct = Math.round(quiz.correct / total * 100);
    header(s.title, "", true);
    progressBar.style.width = "100%";
    if (total >= 10) {
      var best = bestOf(s.id);
      if (best == null || pct > best) save("best:" + s.id, pct);
    }
    view.innerHTML = "";
    var card = el("div", "card score");
    card.innerHTML = '<div class="big">' + pct + "%</div>" +
      '<div class="muted">Правильно ' + quiz.correct + " из " + total + "</div>" +
      '<div class="grade">Оценка: ' + grade(pct) + "</div>";
    view.appendChild(card);

    var again = el("button", "btn primary", "Пройти ещё раз");
    again.onclick = function () { history.back(); };
    view.appendChild(again);
    if (quiz.wrong.length) {
      var redo = el("button", "btn", "Повторить ошибки (" + quiz.wrong.length + ")");
      var wrongIds = quiz.wrong.map(function (w) { return w.q.n; });
      redo.onclick = function () { start(s, wrongIds); };
      view.appendChild(redo);
      view.appendChild(el("h3", "", "Ошибки"));
      quiz.wrong.forEach(function (w) {
        var c = el("div", "card mistake");
        c.innerHTML = '<div class="qnum">Вопрос № ' + w.q.n + "</div>" +
          '<p class="qtext">' + esc(w.q.text) + "</p>" +
          '<div class="your">Ваш ответ: ' + esc(w.your) + "</div>" +
          '<div class="right">Правильно: ' + esc(w.right) + "</div>";
        view.appendChild(c);
      });
    }
    var home = el("button", "btn", "К списку предметов");
    home.onclick = function () { quiz = null; go("#/"); };
    view.appendChild(home);
  }

  route();
})();
