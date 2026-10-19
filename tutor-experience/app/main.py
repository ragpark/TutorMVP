"""HTTP surface: the chat UI and its API, and the webhook the map's evaluation harness drives."""
import asyncio
import hmac
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import anthropic
import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import get_settings
from .map_client import MapClient
from .model import ClaudeModel
from .turn import Deps, harness_turn, ui_turn

log = logging.getLogger("tutor")
STATIC = Path(__file__).resolve().parent.parent / "static"


def create_app(deps: Deps | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if deps is None:
            s = get_settings()
            app.state.deps = Deps(settings=s, map=MapClient(s), model=ClaudeModel(s))
        else:
            app.state.deps = deps
        yield
        if deps is None:
            await app.state.deps.map.aclose()

    app = FastAPI(title="tutor-experience", version="0.1.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/health")
    def health(request: Request):
        s = request.app.state.deps.settings
        return {"ok": True, "map": s.map_base_url, "model": s.model, "has_api_key": bool(s.anthropic_api_key),
                "has_secret": bool(s.tutor_secret)}

    # ------------------------------------------------------------------ UI
    @app.get("/api/pupils")
    async def pupils(request: Request):
        try:
            return await request.app.state.deps.map.pupils()
        except httpx.HTTPError as e:
            raise HTTPException(502, f"could not load pupils from the map ({type(e).__name__})")

    class TurnIn(BaseModel):
        pupil: str = Field(min_length=1, max_length=80)
        subject: Literal["maths", "english"]
        message: str = Field(min_length=1, max_length=4000)
        conversation_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")
        record_evidence: bool = True
        elapsed_s: float | None = None

    @app.post("/api/turn")
    async def turn(t: TurnIn, request: Request):
        try:
            r = await ui_turn(request.app.state.deps, pupil_id=t.pupil, subject=t.subject, message=t.message,
                              conversation_id=t.conversation_id, record_evidence=t.record_evidence,
                              elapsed_s=t.elapsed_s)
        except anthropic.AnthropicError as e:
            log.exception("model call failed")
            raise HTTPException(502, f"the tutor model is unavailable ({type(e).__name__})")
        ev = r.evidence
        return {"turn_id": r.turn_id, "reply": r.reply, "briefing_ok": r.briefing_ok, "briefing_error": r.briefing_error,
                "focus": r.focus,
                "evidence": None if ev is None else {"ok": ev["result"].get("ok"), "score": ev["payload"]["score"],
                                                     "activity": ev["payload"]["activity"]}}

    # ------------------------------------------------------------------ evaluation harness
    class HarnessIn(BaseModel):
        turn_id: str = Field(min_length=1, max_length=200)
        subject: Literal["maths", "english"]
        arm: Literal["none", "raw", "h2"]
        pupil: str = ""
        message: str = Field(min_length=1, max_length=8000)
        context: dict = Field(default_factory=dict)

    @app.post("/webhook/tutor")
    async def webhook(body: HarnessIn, request: Request, x_tutor_secret: str | None = Header(default=None)):
        d: Deps = request.app.state.deps
        if d.settings.tutor_secret and not hmac.compare_digest((x_tutor_secret or "").encode(),
                                                               d.settings.tutor_secret.encode()):
            raise HTTPException(401, "bad or missing X-Tutor-Secret")
        try:
            reply = await asyncio.wait_for(
                harness_turn(d, turn_id=body.turn_id, subject=body.subject, arm=body.arm, pupil=body.pupil,
                             message=body.message, context=body.context),
                timeout=d.settings.webhook_budget_s)
        except asyncio.TimeoutError:
            return JSONResponse({"error": f"turn exceeded the {d.settings.webhook_budget_s:g} s budget"}, status_code=504)
        except anthropic.AnthropicError as e:
            log.exception("model call failed")
            return JSONResponse({"error": f"model unavailable ({type(e).__name__})"}, status_code=502)
        return {"reply": reply}

    return app


app = create_app()
