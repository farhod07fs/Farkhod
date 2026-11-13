(function () {
  "use strict";

  var TESTS = window.TESTS || [];
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
  function mistakesOf(tn) { return load("mistakes:t" + tn, []); }
  function bestOf(tn) { return load("best:t" + tn, null); }

  // ---------- утилиты ----------
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  // Текст с дробями: {3/8} — дробь «столбиком», 2{1/4} — смешанное число.
  function fmt(s) {
    return esc(s).replace(/\{([^{}\/]+)\/([^{}]+)\}/g,
      '<span class="frac"><span>$1</span><span>$2</span></span>');
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
  function test(tn) {
    for (var i = 0; i < TESTS.length; i++) if (TESTS[i].n === tn) return TESTS[i];
    return null;
  }
  // Идентификатор вопроса: «тест-вариант-номер», например «5-2-3».
  function qid(t, v, n) { return t + "-" + v + "-" + n; }
  function byId(id) {
    var p = id.split("-").map(Number), t = test(p[0]);
    var q = t && t.variants[p[1] - 1] && t.variants[p[1] - 1][p[2] - 1];
    return q ? { t: t, v: p[1], q: q, id: id } : null;
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

  // ---------- навигация (через hash, чтобы работала кнопка «Назад» Android) ----------
  function go(hash) { if (location.hash === hash) route(); else location.hash = hash; }
  backBtn.onclick = function () { history.back(); };
  window.addEventListener("hashchange", route);

  function route() {
    var h = location.hash.replace(/^#\/?/, "").split("/");
    if (h[0] === "t" && test(+h[1])) { quiz = null; return showTest(test(+h[1])); }
    if (h[0] === "q" && quiz) return showQuestion();
    if (h[0] === "r" && quiz) return showResult();
    quiz = null;
    showHome();
  }

  // ---------- экраны ----------
  function showHome() {
    header("Математика 5 · Виленкин", "", false);
    view.innerHTML = "";
    var total = 0, all = [];
    TESTS.forEach(function (t) {
      t.variants.forEach(function (v, vi) {
        v.forEach(function (q) { all.push(qid(t.n, vi + 1, q.n)); total++; });
      });
    });
    view.appendChild(el("p", "muted", "Тесты к учебнику Н. Я. Виленкина. " + TESTS.length +
      " тестов, " + total + " вопросов. Ответы — из ключа сборника."));
    var mix = el("button", "btn primary", "Случайные " + RANDOM_COUNT + " вопросов<small>из всех тестов</small>");
    mix.onclick = function () { start("Случайные вопросы", null, shuffle(all).slice(0, RANDOM_COUNT)); };
    view.appendChild(mix);

    var list = el("div", "subjects");
    TESTS.forEach(function (t) {
      var b = el("button", "subject");
      var best = bestOf(t.n);
      var count = t.variants[0].length + t.variants[1].length;
      b.innerHTML = '<span class="testnum">' + t.n + "</span>" +
        '<span><div class="name">' + esc(t.title) + '</div><div class="meta">2 варианта · ' + count + " вопросов</div></span>" +
        (best != null ? '<span class="best">' + best + "%</span>" : "");
      b.onclick = function () { go("#/t/" + t.n); };
      list.appendChild(b);
    });
    view.appendChild(list);
  }

  function showTest(t) {
    header("Тест " + t.n, "", true);
    view.innerHTML = "";
    var best = bestOf(t.n);
    var info = el("div", "card");
    info.innerHTML = "<div><b>Тест " + t.n + ". " + esc(t.title) + "</b></div>" +
      (best != null ? '<div class="muted">Лучший результат: ' + best + "%</div>" : "");
    view.appendChild(info);

    function ids(vi) { return t.variants[vi - 1].map(function (q) { return qid(t.n, vi, q.n); }); }
    function modeBtn(label, sub, list, primary) {
      var b = el("button", "btn" + (primary ? " primary" : ""), esc(label) + "<small>" + esc(sub) + "</small>");
      b.disabled = !list.length;
      b.onclick = function () { start("Тест " + t.n, t.n, list); };
      view.appendChild(b);
    }
    modeBtn("Вариант 1", t.variants[0].length + " вопросов", ids(1), true);
    modeBtn("Вариант 2", t.variants[1].length + " вопросов", ids(2), true);
    modeBtn("Оба варианта вперемешку", (t.variants[0].length + t.variants[1].length) + " вопросов", shuffle(ids(1).concat(ids(2))));
    var mistakes = mistakesOf(t.n).filter(byId);
    modeBtn("Работа над ошибками", mistakes.length ? mistakes.length + " вопросов, где были ошибки" : "ошибок пока нет", mistakes);
  }

  function start(title, tn, ids) {
    quiz = { title: title, tn: tn, list: ids.map(byId).filter(Boolean), pos: 0, correct: 0, wrong: [], answered: false };
    // С экрана теста — новая запись в истории (Назад вернёт к выбору варианта),
    // с главного экрана и экрана результата — замена, чтобы не копить историю.
    if (location.hash.indexOf("#/t/") === 0) go("#/q");
    else if (location.hash.indexOf("#/r") === 0) location.replace("#/q");
    else go("#/q");
  }

  function label(item) { return "Тест " + item.t.n + " · Вариант " + item.v + " · № " + item.q.n; }

  function showQuestion() {
    var item = quiz.list[quiz.pos], q = item.q;
    quiz.answered = false;
    header(quiz.title, (quiz.pos + 1) + " / " + quiz.list.length, true);
    progressBar.style.width = (quiz.pos / quiz.list.length * 100) + "%";
    view.innerHTML = "";

    var card = el("div", "card");
    card.appendChild(el("div", "qnum", esc(label(item)) + (q.note ? " ⚠" : "")));
    card.appendChild(el("p", "qtext", fmt(q.text)));
    if (q.fig) {
      var img = el("img", "fig");
      img.src = q.fig;
      img.alt = "Рисунок к заданию";
      card.appendChild(img);
    }
    view.appendChild(card);

    var area = el("div"), feedback = el("div");
    view.appendChild(area);
    view.appendChild(feedback);

    var buttons = q.options.map(function (text, i) {
      var b = el("button", "btn opt", '<span class="letter">' + (i + 1) + "</span><span>" + fmt(text) + "</span>");
      b.onclick = function () {
        if (quiz.answered) return;
        var ok = i === q.answer;
        buttons[q.answer].classList.add("ok");
        if (!ok) b.classList.add("bad");
        finish(item, ok, (i + 1) + ") " + text, (q.answer + 1) + ") " + q.options[q.answer], feedback);
      };
      area.appendChild(b);
      return b;
    });
  }

  function explainBox(q) {
    var box = el("div", "card explain");
    box.appendChild(el("div", "explain-title", "Разъяснение"));
    box.appendChild(el("p", "", fmt(q.explain)));
    if (q.note) box.appendChild(el("p", "note-box", "⚠ " + fmt(q.note)));
    return box;
  }

  function finish(item, ok, yourText, rightText, feedback) {
    quiz.answered = true;
    if (ok) quiz.correct++;
    else quiz.wrong.push({ item: item, your: yourText, right: rightText });

    var key = "mistakes:t" + item.t.n;
    var mistakes = mistakesOf(item.t.n).filter(function (id) { return id !== item.id; });
    if (!ok) mistakes.push(item.id);
    save(key, mistakes);

    feedback.innerHTML = "";
    feedback.appendChild(el("p", "feedback " + (ok ? "ok" : "bad"),
      ok ? "✔ Верно!" : "✘ Неверно. Правильный ответ: " + fmt(rightText)));
    var box = explainBox(item.q);
    if (ok) {
      // при верном ответе разъяснение открывается по кнопке
      box.hidden = true;
      var show = el("button", "btn", "Показать разъяснение");
      show.onclick = function () { box.hidden = false; show.remove(); };
      feedback.appendChild(show);
    }
    feedback.appendChild(box);
    var last = quiz.pos === quiz.list.length - 1;
    var next = el("button", "btn primary", last ? "Показать результат" : "Следующий вопрос →");
    next.onclick = function () {
      if (quiz.pos < quiz.list.length - 1) { quiz.pos++; showQuestion(); }
      else location.replace("#/r");
    };
    feedback.appendChild(next);
    next.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function showResult() {
    var total = quiz.list.length;
    var pct = Math.round(quiz.correct / total * 100);
    header(quiz.title, "", true);
    progressBar.style.width = "100%";
    if (quiz.tn != null) {
      var best = bestOf(quiz.tn);
      if (best == null || pct > best) save("best:t" + quiz.tn, pct);
    }
    view.innerHTML = "";
    var card = el("div", "card score");
    card.innerHTML = '<div class="big">' + pct + "%</div>" +
      '<div class="muted">Правильно ' + quiz.correct + " из " + total + "</div>" +
      '<div class="grade">Оценка: ' + grade(pct) + "</div>";
    view.appendChild(card);

    var again = el("button", "btn primary", quiz.tn != null ? "К выбору варианта" : "На главную");
    again.onclick = function () { history.back(); };
    view.appendChild(again);
    if (quiz.wrong.length) {
      var redo = el("button", "btn", "Повторить ошибки (" + quiz.wrong.length + ")");
      var wrongIds = quiz.wrong.map(function (w) { return w.item.id; });
      var title = quiz.title, tn = quiz.tn;
      redo.onclick = function () { start(title, tn, wrongIds); };
      view.appendChild(redo);
      view.appendChild(el("h3", "", "Ошибки"));
      quiz.wrong.forEach(function (w) {
        var c = el("div", "card mistake");
        c.innerHTML = '<div class="qnum">' + esc(label(w.item)) + "</div>" +
          '<p class="qtext">' + fmt(w.item.q.text) + "</p>" +
          '<div class="your">Ваш ответ: ' + fmt(w.your) + "</div>" +
          '<div class="right">Правильно: ' + fmt(w.right) + "</div>" +
          '<p class="muted">' + fmt(w.item.q.explain) + "</p>";
        view.appendChild(c);
      });
    }
    var home = el("button", "btn", "К списку тестов");
    home.onclick = function () { quiz = null; go("#/"); };
    view.appendChild(home);
  }

  route();
})();
