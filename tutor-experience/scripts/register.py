"""Register this tutor's webhook with the map's evaluation harness.

  MAP_BASE_URL=... TUTOR_PUBLIC_URL=https://<this deployment> TUTOR_SECRET=... python -m scripts.register
"""
import argparse
import asyncio
import json
import os
import sys

from app.config import get_settings
from app.map_client import MapClient


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=os.environ.get("TUTOR_PUBLIC_URL"), help="public base URL of this tutor")
    ap.add_argument("--label", default="tutor-experience v0.1")
    args = ap.parse_args()
    if not args.url:
        print("Set TUTOR_PUBLIC_URL (or pass --url) to the deployed tutor's public base URL.", file=sys.stderr)
        return 2
    s = get_settings()
    if not s.tutor_secret:
        print("Warning: TUTOR_SECRET is empty, so the webhook will accept unsigned calls.", file=sys.stderr)
    hook = args.url.rstrip("/") + "/webhook/tutor"
    client = MapClient(s)
    try:
        t = await client.register_tutor(args.label, hook, s.tutor_secret)
    finally:
        await client.aclose()
    print(json.dumps(t, indent=2))
    print(f"\nRegistered {hook} with {s.map_base_url}. Check it with: POST {s.map_base_url}/api/tutors/{t['id']}/ping",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
