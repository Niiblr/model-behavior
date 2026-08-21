"""Dynamic discovery of zero-cost OpenRouter models via the models.dev catalog.

The models.dev catalog (used by opencode) lists every provider/model with its
pricing. We filter for OpenRouter models whose input and output cost are both
zero, exclude obviously non-chat models, and expose a clean roster that can be
used to assemble an ad-hoc debate council without any paid API usage.
"""

import time
from typing import Any, Dict, List

import httpx

MODELS_DEV_URL = "https://models.dev/api.json"
CACHE_TTL_SECONDS = 3600.0
FETCH_TIMEOUT = 30.0

# In-memory cache: {"fetched_at": float, "models": [...]}
_cache: Dict[str, Any] = {"fetched_at": 0.0, "models": []}

# Substrings that identify non-chat / specialized endpoints we never want in a debate
_EXCLUDED_ID_SUBSTRINGS = (
    "content-safety",
    "guard",
    "moderation",
    "embed",
    "rerank",
    "whisper",
    "tts",
    "transcribe",
    "image",
    "diffusion",
    "video",
)

# Roles that make poor debate participants even though they are free chat models
_EXCLUDED_NAME_SUBSTRINGS = (
    "content safety",
)


def _clean_name(name: str, model_id: str) -> str:
    """Clean up the display name (strip '(free)' suffixes etc.)."""
    base = (name or "").strip() or model_id
    for suffix in ("(free)", "(Free)", "(FREE)"):
        if base.endswith(suffix):
            base = base[: -len(suffix)].strip()
    return base or model_id


def _is_excluded(model_id: str, name: str) -> bool:
    mid = model_id.lower()
    if any(p in mid for p in _EXCLUDED_ID_SUBSTRINGS):
        return True
    lname = name.lower()
    return any(p in lname for p in _EXCLUDED_NAME_SUBSTRINGS)


def _extract_free_models(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pull all zero-cost OpenRouter chat models out of a models.dev catalog."""
    results: List[Dict[str, Any]] = []
    openrouter_entry = catalog.get("openrouter") or {}
    models = openrouter_entry.get("models") or {}

    for model_id, info in models.items():
        cost = info.get("cost") or {}
        try:
            input_free = float(cost.get("input") or 0) == 0
            output_free = float(cost.get("output") or 0) == 0
        except (TypeError, ValueError):
            continue
        if not (input_free and output_free):
            continue

        name = _clean_name(info.get("name"), model_id)
        if _is_excluded(model_id, name):
            continue

        limit = info.get("limit") or {}
        results.append({
            "id": model_id,
            "name": name,
            "context_length": limit.get("context"),
            "description": (info.get("description") or "")[:200],
        })

    results.sort(key=lambda m: m["name"].lower())
    return results


async def get_free_models(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Return the cached list of free OpenRouter models, refreshing from
    models.dev when the cache is stale (1 hour TTL).
    """
    now = time.time()
    if not force_refresh and _cache["models"] and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
        return _cache["models"]

    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT) as client:
        response = await client.get(MODELS_DEV_URL)
        response.raise_for_status()
        catalog = response.json()

    _cache["models"] = _extract_free_models(catalog)
    _cache["fetched_at"] = now
    print(f"[freemodels] Refreshed catalog: {len(_cache['models'])} free models available")
    return _cache["models"]


def clear_cache():
    """Reset the cache (mainly useful for testing)."""
    _cache["fetched_at"] = 0.0
    _cache["models"] = []
