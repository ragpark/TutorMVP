"""Conversation transcripts, one JSON-lines file per conversation. This is the only conversation state we keep;
everything about the pupil lives in the map."""
import datetime as dt
import json
import re
from pathlib import Path

from .config import Settings

ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def _path(settings: Settings, conversation_id: str) -> Path:
    if not ID_RE.match(conversation_id):
        raise ValueError("bad conversation id")
    d = settings.data_dir / "transcripts"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{conversation_id}.jsonl"


def history(settings: Settings, conversation_id: str) -> list[dict]:
    """Earlier turns as alternating user/assistant messages, ready for the model."""
    p = _path(settings, conversation_id)
    if not p.exists():
        return []
    msgs = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    return [{"role": m["role"], "content": m["content"]} for m in msgs]


def append(settings: Settings, conversation_id: str, *, pupil: str, turn_id: str, user: str, assistant: str) -> None:
    ts = dt.datetime.now(dt.timezone.utc).isoformat()
    with _path(settings, conversation_id).open("a") as f:
        for role, content in (("user", user), ("assistant", assistant)):
            f.write(json.dumps({"ts": ts, "turn_id": turn_id, "pupil": pupil, "role": role, "content": content},
                               ensure_ascii=False) + "\n")
