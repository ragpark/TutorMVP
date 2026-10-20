"""One Claude call per turn. Every call is logged to disk as JSON (full prompt and full response) for inspection."""
import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import anthropic

from . import widgets as W
from .config import Settings
from .prompting import Prompt

BLOCK_RE = {tag: re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL) for tag in ("assessment", "widgets")}
FALLBACK_REPLY = "Sorry, I lost my train of thought there. Could you send that again?"
REFUSAL_REPLY = "I can't help with that one. Shall we get back to your work?"


@dataclass
class ModelResult:
    text: str
    model: str
    stop_reason: str | None = None
    raw: dict = field(default_factory=dict)


class ModelUnavailable(Exception):
    """The model could not be called: no credentials, network failure, or an API error."""


class ModelCaller(Protocol):
    async def __call__(self, prompt: Prompt) -> ModelResult: ...


class ClaudeModel:
    """The real caller. Tests swap in a fake with the same signature."""

    def __init__(self, settings: Settings, timeout_s: float = 45.0):
        self.settings = settings
        self.timeout_s = timeout_s
        self._client: anthropic.AsyncAnthropic | None = None

    async def __call__(self, prompt: Prompt) -> ModelResult:
        if self._client is None:  # created on first use so the app can start (and serve the UI) without a key
            self._client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key, timeout=self.timeout_s,
                                                    max_retries=1)
        try:
            r = await self._client.messages.create(model=self.settings.model, max_tokens=self.settings.max_tokens,
                                                   system=prompt.system, messages=prompt.messages)
        except anthropic.AnthropicError as e:
            raise ModelUnavailable(type(e).__name__) from e
        except TypeError as e:  # the SDK's "could not resolve authentication method"
            raise ModelUnavailable("no Anthropic credentials (set ANTHROPIC_API_KEY)") from e
        text = "".join(b.text for b in r.content if b.type == "text")
        return ModelResult(text=text, model=r.model, stop_reason=r.stop_reason, raw=r.model_dump(mode="json"))


@dataclass
class TurnOutput:
    reply: str
    assessment: dict | None
    log_path: Path
    widgets: list[dict] = field(default_factory=list)


def _block(text: str, tag: str):
    m = BLOCK_RE[tag].search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return None


def split_reply(text: str) -> tuple[str, dict | None, list[dict]]:
    """Separate the pupil-facing reply from the hidden assessment and widgets blocks. Malformed blocks are dropped,
    never shown."""
    assessment = _block(text, "assessment")
    reply = text
    for rx in BLOCK_RE.values():
        reply = rx.sub("", reply)
    reply = re.sub(r"</?(assessment|widgets)>.*", "", reply, flags=re.DOTALL)  # an unclosed block
    return reply.strip(), assessment if isinstance(assessment, dict) else None, W.clean(_block(text, "widgets"))


def log_dir(settings: Settings) -> Path:
    d = settings.data_dir / "turns" / dt.date.today().isoformat()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe(turn_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]", "_", turn_id)[:120].replace(":", "_")


def write_log(path: Path, record: dict) -> None:
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str))


def append_to_log(path: Path, **fields) -> None:
    rec = json.loads(path.read_text())
    rec.update(fields)
    write_log(path, rec)


async def run_model(caller: ModelCaller, prompt: Prompt, settings: Settings, turn_id: str, meta: dict) -> TurnOutput:
    path = log_dir(settings) / f"{_safe(turn_id)}.json"
    record = {"turn_id": turn_id, "ts": dt.datetime.now(dt.timezone.utc).isoformat(), "model": settings.model,
              "condition": prompt.condition, **meta,
              "prompt": {"system": prompt.system, "messages": prompt.messages}}
    try:
        result = await caller(prompt)
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
        write_log(path, record)
        raise
    reply, assessment, widgets = split_reply(result.text)
    if result.stop_reason == "refusal":
        reply, assessment, widgets = REFUSAL_REPLY, None, []
    if not reply:
        reply = FALLBACK_REPLY
    record.update(response={"text": result.text, "model": result.model, "stop_reason": result.stop_reason,
                            "raw": result.raw},
                  reply=reply, assessment=assessment, widgets=widgets)
    write_log(path, record)
    return TurnOutput(reply=reply, assessment=assessment, log_path=path, widgets=widgets)
