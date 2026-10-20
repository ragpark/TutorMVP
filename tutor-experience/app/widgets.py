"""Interactive widgets the model may attach to a reply, for the UI only.

The vocabulary is fixed and every widget is validated here: unknown types and fields are dropped, strings are clipped,
and at most MAX_WIDGETS survive. The webhook never returns widgets, so the text reply must stand on its own.
"""

MAX_WIDGETS = 3
TYPES = ("steps", "hints", "answer", "balance", "bar_model", "number_line", "function_machine", "quote", "confidence")


def _s(v, n: int = 160) -> str | None:
    if not isinstance(v, (str, int, float)) or isinstance(v, bool):
        return None
    s = " ".join(str(v).split())
    return (s if len(s) <= n else s[: n - 1] + "…") or None


def _strs(v, n: int = 160, k: int = 6) -> list[str]:
    return [x for x in (_s(i, n) for i in (v if isinstance(v, list) else [])[:k]) if x]


def _num(v, lo: float = -1e6, hi: float = 1e6) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if lo <= v <= hi else None


def _clean(w: dict) -> dict | None:
    t = w.get("type")
    if t == "steps":
        steps = _strs(w.get("steps"), 200)
        return {"type": t, "title": _s(w.get("title"), 80), "steps": steps} if steps else None
    if t == "hints":
        hints = _strs(w.get("hints"), 200, 4)
        return {"type": t, "hints": hints} if hints else None
    if t == "answer":
        choices = _strs(w.get("choices"), 60, 5)
        prompt = _s(w.get("prompt"), 120)
        return {"type": t, "prompt": prompt or "Your answer", "choices": choices} if (prompt or choices) else None
    if t == "balance":
        left, right = _s(w.get("left"), 40), _s(w.get("right"), 40)
        if not (left and right):
            return None
        out = {"type": t, "left": left, "right": right, "operation": _s(w.get("operation"), 60)}
        rl, rr = _s(w.get("result_left"), 40), _s(w.get("result_right"), 40)
        if rl and rr:
            out |= {"result_left": rl, "result_right": rr}
        return out
    if t == "bar_model":
        rows = []
        for r in (w.get("rows") if isinstance(w.get("rows"), list) else [])[:4]:
            if not isinstance(r, dict):
                continue
            segs = []
            for sg in (r.get("segments") if isinstance(r.get("segments"), list) else [])[:12]:
                if isinstance(sg, dict) and _s(sg.get("label"), 16):
                    size = _num(sg.get("size"), 0.1, 100) or 1.0
                    segs.append({"label": _s(sg.get("label"), 16), "size": size})
            if segs:
                rows.append({"label": _s(r.get("label"), 30), "segments": segs})
        return {"type": t, "rows": rows, "caption": _s(w.get("caption"), 120)} if rows else None
    if t == "number_line":
        lo, hi = _num(w.get("min"), -1000, 1000), _num(w.get("max"), -1000, 1000)
        if lo is None or hi is None or not (0 < hi - lo <= 40):
            return None
        marks = []
        for m in (w.get("marks") if isinstance(w.get("marks"), list) else [])[:6]:
            v = _num(m.get("value"), lo, hi) if isinstance(m, dict) else None
            if v is not None:
                marks.append({"value": v, "label": _s(m.get("label"), 16)})
        return {"type": t, "min": lo, "max": hi, "marks": marks, "caption": _s(w.get("caption"), 120)}
    if t == "function_machine":
        ops = _strs(w.get("operations"), 16, 4)
        return {"type": t, "input": _s(w.get("input"), 16) or "?", "operations": ops,
                "output": _s(w.get("output"), 16) or "?"} if ops else None
    if t == "quote":
        text = _s(w.get("text"), 300)
        if not text:
            return None
        return {"type": t, "text": text, "speaker": _s(w.get("speaker"), 40), "act": _s(w.get("act"), 12),
                "focus_words": [f for f in _strs(w.get("focus_words"), 30, 4) if f.lower() in text.lower()],
                "question": _s(w.get("question"), 160)}
    if t == "confidence":
        return {"type": t, "prompt": _s(w.get("prompt"), 100) or "How sure are you?"}
    return None


def clean(raw) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out = []
    for w in raw:
        c = _clean(w) if isinstance(w, dict) and w.get("type") in TYPES else None
        if c:
            out.append({k: v for k, v in c.items() if v not in (None, [], "")} | {"type": c["type"]})
        if len(out) == MAX_WIDGETS:
            break
    return out
