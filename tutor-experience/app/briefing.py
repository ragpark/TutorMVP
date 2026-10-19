"""Fetch the briefing for one turn from the map. If the map can't be reached, say so; never invent context."""
from dataclasses import dataclass

import httpx

from .map_client import MapClient


@dataclass
class BriefingResult:
    briefing: dict | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.briefing is not None


async def fetch_briefing(client: MapClient, pupil_id: str, message: str, concept: str | None = None) -> BriefingResult:
    try:
        b = await client.context(pupil_id, message, concept)
    except httpx.HTTPStatusError as e:
        return BriefingResult(None, f"the map returned HTTP {e.response.status_code}")
    except httpx.HTTPError as e:
        return BriefingResult(None, f"the map could not be reached ({type(e).__name__})")
    except ValueError:
        return BriefingResult(None, "the map returned something that was not JSON")
    if not isinstance(b, dict) or "focus" not in b:
        return BriefingResult(None, "the map returned a response that was not a briefing")
    return BriefingResult(b)
