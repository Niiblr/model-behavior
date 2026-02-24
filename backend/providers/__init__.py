"""Provider abstraction layer for multi-provider LLM support."""

from typing import List, Dict, Any, Optional
import asyncio

OPENROUTER_STAGGER_DELAY = 5  # seconds between each OpenRouter request


class Provider:
    """Base class for LLM providers."""

    async def query(
        self,
        model: str,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


async def query_model(
    provider: Provider,
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query a single model through its provider."""
    return await provider.query(model, messages, timeout)


async def _staggered_query(provider, model, name, messages, delay):
    """Wait for delay seconds then query the model."""
    if delay > 0:
        await asyncio.sleep(delay)
    response = await query_model(provider, model, messages, timeout=300.0)
    return name, response


async def query_models_parallel(
    model_configs: List[Dict[str, Any]],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models, firing non-OpenRouter models in parallel immediately
    and staggering OpenRouter models to avoid rate limits.
    """
    from .openrouter import OpenRouterProvider

    tasks = []
    openrouter_count = 0

    for config in model_configs:
        provider = config['provider']
        model = config['model']
        name = config.get('name', model)

        if isinstance(provider, OpenRouterProvider):
            delay = openrouter_count * OPENROUTER_STAGGER_DELAY
            openrouter_count += 1
        else:
            delay = 0

        tasks.append(_staggered_query(provider, model, name, messages, delay))

    results = await asyncio.gather(*tasks)

    return {name: response for name, response in results}