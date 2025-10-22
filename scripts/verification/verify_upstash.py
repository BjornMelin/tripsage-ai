"""Verify Upstash Redis connectivity and basic operations.

Run from project root:
    uv run python scripts/verification/verify_upstash.py
Requires env vars:
    - UPSTASH_REDIS_REST_URL
    - UPSTASH_REDIS_REST_TOKEN
"""

from __future__ import annotations

import asyncio
import os

from upstash_redis.asyncio import Redis


async def main() -> int:
    """Run a simple connectivity+CRUD check against Upstash Redis.

    Returns:
        Process exit code (0 on success, non-zero on failure).
    """
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        print("Missing UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN")
        return 1

    client = Redis(url=url, token=token)

    # Ping
    pong = await client.ping()
    print(f"Ping: {pong}")

    # Set/Get
    ok = await client.set("verify:tripsage", "ok", ex=30)
    print(f"Set: {ok}")
    val = await client.get("verify:tripsage")
    print(f"Get: {val}")

    # TTL
    ttl = await client.ttl("verify:tripsage")
    print(f"TTL: {ttl}")

    # Cleanup
    await client.delete("verify:tripsage")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
