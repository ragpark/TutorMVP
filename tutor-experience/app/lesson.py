"""What the UI's lesson panel shows, taken from the briefing. Class-level facts only (topic, scheme of work, method,
next step), never labels about the pupil: the map's rule is that the pupil is not described with a label."""


def _week(item: str) -> tuple[int | None, str]:
    head, _, rest = item.partition(" ")
    if head.startswith("Wk") and head[2:].isdigit():
        return int(head[2:]), rest
    return None, item


def lesson_view(b: dict | None) -> dict | None:
    if not b:
        return None
    focus, cls, g = b.get("focus") or {}, b.get("class") or {}, b.get("guidance") or {}
    tw, ns = g.get("teach_with") or {}, g.get("next_step") or {}
    next_label = ((ns.get("after_that") or {}).get("label") if ns.get("action") == "consolidate"
                  else (ns.get("concept") or {}).get("label"))
    scheme = []
    for status, items in (("taught", cls.get("taught_so_far") or []), ("coming", cls.get("not_yet_taught") or [])):
        for it in items:
            wk, label = _week(it)
            scheme.append({"week": wk, "label": label, "status": status, "focus": label == focus.get("label")})
    return {
        "subject": b.get("subject"),
        "topic": focus.get("label"),
        "topic_taught": cls.get("focus_taught"),
        "topic_week": cls.get("focus_week"),
        "current_week": cls.get("current_week"),
        "class": cls.get("id"),
        "method": (tw.get("method") or {}).get("label"),
        "representation": (tw.get("representation") or {}).get("label"),
        "next": next_label if next_label != focus.get("label") else None,
        "scheme": scheme,
        "text_studied": cls.get("text_studied_so_far"),
        "text_coming": cls.get("text_coming_up"),
    }
