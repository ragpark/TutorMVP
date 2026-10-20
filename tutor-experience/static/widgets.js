// Interactive widgets under a tutor reply. Every widget is built with DOM APIs from validated server data (never
// innerHTML), and talks back through ctx: send(text) posts a pupil message, event(type, extra) queues a process event
// for the map, speak(text) reads aloud.
(function () {
  const SVG = "http://www.w3.org/2000/svg";

  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") n.className = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v === true ? "" : v);
    }
    for (const c of kids.flat()) if (c !== null && c !== undefined) n.append(c);
    return n;
  }

  function svg(tag, attrs, ...kids) {
    const n = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
    for (const c of kids) n.append(c);
    return n;
  }

  function frame(title, ...kids) {
    return el("div", { class: "w" }, title ? el("h3", {}, title) : null, ...kids);
  }

  // ---------------------------------------------------------------- one-at-a-time reveal (steps, hints)
  function reveal(title, items, firstLabel, nextLabel, onReveal) {
    const list = el("ol", { class: "reveal" });
    const btn = el("button", { type: "button" }, firstLabel);
    const box = frame(title, list, btn);
    let shown = 0;
    btn.addEventListener("click", () => {
      list.append(el("li", {}, items[shown]));
      shown += 1;
      if (onReveal) onReveal(shown);
      if (shown >= items.length) btn.remove();
      else btn.textContent = `${nextLabel} (${shown + 1} of ${items.length})`;
    });
    return box;
  }

  const renderers = {
    steps(w) {
      const title = w.title || "Worked example";
      return reveal(title, w.steps, w.steps.length > 1 ? `Show step 1 of ${w.steps.length}` : "Show the step", "Next step");
    },

    hints(w, ctx) {
      return reveal("Hints", w.hints, "I'd like a hint", "Another hint", () => ctx.event("hint_requested"));
    },

    answer(w, ctx) {
      const box = frame("Your answer");
      if (w.choices && w.choices.length) {
        box.append(el("p", { class: "prompt" }, w.prompt),
          el("div", { class: "row" }, w.choices.map((c) => el("button", { type: "button", onclick: () => ctx.send(c) }, c))));
        return box;
      }
      const input = el("input", { type: "text", "aria-label": w.prompt, autocomplete: "off", spellcheck: "false" });
      const submit = () => {
        const v = input.value.trim();
        if (!v) return input.focus();
        ctx.send(/[=:]\s*$/.test(w.prompt) ? `${w.prompt.trim()} ${v}` : v);
      };
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); submit(); } });
      box.append(el("div", { class: "row" }, el("span", { class: "prompt" }, w.prompt), input,
        el("button", { type: "button", class: "primary", onclick: submit }, "Check")));
      return box;
    },

    confidence(w, ctx) {
      const labels = ["Guessing", "Not sure", "Fairly sure", "Certain"];
      const row = el("div", { class: "scale", role: "group", "aria-label": w.prompt });
      const note = el("p", { class: "done-note", hidden: true });
      labels.forEach((label, i) => row.append(el("button", {
        type: "button",
        onclick: (e) => {
          row.querySelectorAll("button").forEach((b) => b.classList.remove("on"));
          e.currentTarget.classList.add("on");
          ctx.event("confidence", { rating: i + 1 });
          note.hidden = false;
          note.textContent = "Thanks. That helps your tutor.";
        },
      }, label)));
      return frame(w.prompt, row, note);
    },

    balance(w) {
      const box = frame("Balance");
      const s = svg("svg", { viewBox: "0 0 340 170", role: "img" });
      const left = svg("text", { x: 80, y: 128, "text-anchor": "middle" });
      const right = svg("text", { x: 260, y: 128, "text-anchor": "middle" });
      const label = () => s.setAttribute("aria-label", `Balance: ${left.textContent} on the left, ${right.textContent} on the right`);
      left.textContent = w.left; right.textContent = w.right;
      s.append(
        svg("line", { class: "line", x1: 170, y1: 40, x2: 170, y2: 140 }),
        svg("path", { class: "line", d: "M145 162 L170 138 L195 162 Z" }),
        svg("line", { class: "line", x1: 30, y1: 40, x2: 310, y2: 40 }),
        svg("line", { class: "line", x1: 80, y1: 40, x2: 80, y2: 100 }),
        svg("line", { class: "line", x1: 260, y1: 40, x2: 260, y2: 100 }),
        svg("rect", { class: "pan", x: 20, y: 100, width: 120, height: 44, rx: 10 }),
        svg("rect", { class: "pan", x: 200, y: 100, width: 120, height: 44, rx: 10 }),
        left, right);
      label();
      box.append(s);
      if (w.operation) box.append(el("p", { class: "caption" }, `Do the same to both sides: ${w.operation}`));
      if (w.result_left && w.result_right) {
        const btn = el("button", { type: "button" }, "Do it to both sides");
        btn.addEventListener("click", () => {
          left.textContent = w.result_left; right.textContent = w.result_right; label();
          btn.replaceWith(el("p", { class: "done-note" }, "Still balanced."));
        });
        box.append(btn);
      }
      return box;
    },

    bar_model(w) {
      const W = 320, rowH = 34, gap = 22;
      const total = Math.max(...w.rows.map((r) => r.segments.reduce((a, sg) => a + sg.size, 0)));
      const h = w.rows.length * (rowH + gap) + 4;
      const s = svg("svg", { viewBox: `0 0 ${W + 20} ${h}`, role: "img", "aria-label": "Bar model" });
      w.rows.forEach((r, i) => {
        const y = i * (rowH + gap) + 18;
        if (r.label) { const t = svg("text", { x: 10, y: y - 5, class: "muted-t" }); t.textContent = r.label; s.append(t); }
        let x = 10;
        r.segments.forEach((sg) => {
          const width = (sg.size / total) * W;
          const t = svg("text", { x: x + width / 2, y: y + rowH / 2 + 5, "text-anchor": "middle" });
          t.textContent = sg.label;
          s.append(svg("rect", { class: "seg", x, y, width, height: rowH, rx: 4 }), t);
          x += width;
        });
      });
      return frame("Bar model", s, w.caption ? el("p", { class: "caption" }, w.caption) : null);
    },

    number_line(w) {
      const W = 320, x0 = 20, span = w.max - w.min;
      const step = span <= 12 ? 1 : span <= 24 ? 2 : 5;
      const X = (v) => x0 + ((v - w.min) / span) * W;
      const s = svg("svg", { viewBox: `0 0 ${W + 40} 80`, role: "img", "aria-label": `Number line from ${w.min} to ${w.max}` });
      s.append(svg("line", { class: "line", x1: x0 - 8, y1: 50, x2: x0 + W + 8, y2: 50 }));
      for (let v = Math.ceil(w.min); v <= w.max; v += 1) {
        const major = v % step === 0;
        s.append(svg("line", { class: "line", x1: X(v), y1: major ? 42 : 46, x2: X(v), y2: major ? 58 : 54 }));
        if (major) { const t = svg("text", { x: X(v), y: 74, "text-anchor": "middle", class: "muted-t" }); t.textContent = v; s.append(t); }
      }
      (w.marks || []).forEach((m) => {
        s.append(svg("circle", { class: "mark", cx: X(m.value), cy: 50, r: 6 }));
        if (m.label) { const t = svg("text", { x: X(m.value), y: 30, "text-anchor": "middle" }); t.textContent = m.label; s.append(t); }
      });
      return frame("Number line", s, w.caption ? el("p", { class: "caption" }, w.caption) : null);
    },

    function_machine(w) {
      const parts = [el("span", { class: "box" }, w.input)];
      w.operations.forEach((op) => parts.push(el("span", { class: "arrow" }, "→"), el("span", { class: "box op" }, op)));
      parts.push(el("span", { class: "arrow" }, "→"), el("span", { class: "box" }, w.output));
      return frame("Function machine", el("div", { class: "machine", role: "img",
        "aria-label": `Function machine: ${w.input}, ${w.operations.join(", then ")}, gives ${w.output}` }, parts));
    },

    quote(w, ctx) {
      const q = el("blockquote", { class: "quote" });
      const words = (w.focus_words || []).map((f) => f.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
      if (words.length) {
        const rx = new RegExp(`(${words.join("|")})`, "gi");
        w.text.split(rx).forEach((part, i) => q.append(i % 2 ? el("mark", {}, part) : part));
      } else q.append(w.text);
      const act = w.act && /^\d+\.\d+$/.test(w.act) ? `Act ${w.act.split(".")[0]}, Scene ${w.act.split(".")[1]}` : w.act;
      const cite = [w.speaker, act].filter(Boolean).join(", ");
      return frame("Look closely", q,
        cite ? el("p", { class: "quote-cite" }, `— ${cite}`) : null,
        w.question ? el("p", { class: "caption" }, w.question) : null,
        el("div", { class: "row" }, el("button", { type: "button", onclick: () => ctx.speak(w.text) }, "🔊 Hear it")));
    },
  };

  function render(list, ctx) {
    const wrap = el("div", { class: "widgets" });
    for (const w of list || []) {
      const fn = renderers[w.type];
      if (!fn) continue;
      try { wrap.append(fn(w, ctx)); } catch (e) { console.warn("widget failed", w, e); }
    }
    return wrap.childElementCount ? wrap : null;
  }

  window.Widgets = { render, el };
})();
