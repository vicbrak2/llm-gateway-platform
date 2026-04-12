from __future__ import annotations

import hashlib
import json
from typing import Any

from redis.asyncio import Redis


class CacheService:
    def __init__(self, redis_client: Redis | None, ttl_seconds: int = 300) -> None:
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def make_key(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"llm_orch:{digest}"

    async def get(self, key: str) -> dict[str, Any] | None:
        if not self.redis:
            return None
        raw = await self.redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: dict[str, Any]) -> None:
        if not self.redis:
            return
        await self.redis.set(key, json.dumps(value, ensure_ascii=False), ex=self.ttl_seconds)
