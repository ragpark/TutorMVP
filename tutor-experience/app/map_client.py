"""Thin client for the Curriculum Map's REST routes. The map owns all pupil and curriculum state."""
import httpx

from .config import Settings


class MapClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self._http = httpx.AsyncClient(base_url=settings.map_base_url, timeout=settings.map_timeout_s, transport=transport)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get(self, path: str, **params):
        r = await self._http.get(path, params={k: v for k, v in params.items() if v is not None})
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, body: dict):
        r = await self._http.post(path, json=body)
        r.raise_for_status()
        return r.json()

    async def subjects(self) -> list[dict]:
        return await self._get("/api/subjects")

    async def pupils(self, subject: str | None = None) -> list[dict]:
        return await self._get("/api/pupils", subject=subject)

    async def classes(self, subject: str | None = None) -> list[dict]:
        return await self._get("/api/classes", subject=subject)

    async def context(self, learner: str, message: str, concept: str | None = None) -> dict:
        return await self._post("/api/context", {"learner": learner, "message": message, "concept": concept})

    async def evidence(self, payload: dict) -> dict:
        return await self._post("/api/evidence", payload)

    async def register_tutor(self, label: str, url: str, secret: str | None) -> dict:
        return await self._post("/api/tutors", {"label": label, "kind": "webhook", "url": url, "secret": secret})
