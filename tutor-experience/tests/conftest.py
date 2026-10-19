import asyncio
import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.map_client import MapClient
from app.model import ModelResult
from app.turn import Deps

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class FakeModel:
    """Stands in for Claude: records each prompt and returns a canned reply (optionally after a delay)."""

    def __init__(self, text: str = "Let's look at that together. What do you get?", delay: float = 0.0):
        self.text, self.delay, self.prompts = text, delay, []

    async def __call__(self, prompt):
        self.prompts.append(prompt)
        if self.delay:
            await asyncio.sleep(self.delay)
        return ModelResult(text=self.text, model="fake-model", stop_reason="end_turn", raw={"fake": True})


class FakeMap:
    """An httpx transport that answers like the map and records every request. No network."""

    def __init__(self, briefing: dict | None = None, down: bool = False):
        self.briefing, self.down, self.requests = briefing, down, []

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        self.requests.append((request.method, request.url.path, body))
        if self.down:
            raise httpx.ConnectError("map down", request=request)
        if request.url.path == "/api/context":
            return httpx.Response(200, json=self.briefing)
        if request.url.path == "/api/evidence":
            return httpx.Response(200, json={"recorded": {"evidence_id": 1, "outcome": body.get("score"),
                                                          "concepts": [], "concept_provenance": "claude"}})
        if request.url.path == "/api/pupils":
            return httpx.Response(200, json=[{"id": "pupil:amara", "name": "Amara (synthetic)", "class": "10X",
                                              "subject": "maths"}])
        return httpx.Response(404, json={"detail": "not found"})

    def paths(self) -> list[str]:
        return [p for _, p, _ in self.requests]


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(map_base_url="http://map.test", anthropic_api_key=None, tutor_secret=None, model="test-model",
                    evidence_from_harness=False, webhook_budget_s=50.0, data_dir=tmp_path)


def make_deps(settings: Settings, fake_map: FakeMap, model: FakeModel) -> Deps:
    return Deps(settings=settings, map=MapClient(settings, transport=httpx.MockTransport(fake_map.handler)), model=model)


def client_for(settings: Settings, fake_map: FakeMap, model: FakeModel) -> TestClient:
    return TestClient(create_app(make_deps(settings, fake_map, model)))


def with_(settings: Settings, **kw) -> Settings:
    return replace(settings, **kw)
