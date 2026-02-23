"""Provider abstraction layer for multi-provider LLM support."""

from typing import List, Dict, Any, Optional
import asyncio


class Provider:
    """Base class for LLM providers."""
    
    async def query(
        self,
        model: str,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """
        Query a model.
        
        Args:
            model: Model identifier
            messages: List of message dicts with 'role' and 'content'
            timeout: Request timeout in seconds
            
        Returns:
            Response dict with 'content' key, or None if failed
        """
        raise NotImplementedError


async def query_model(
    provider: Provider,
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query a single model through its provider."""
    return await provider.query(model, messages, timeout)


async def query_models_parallel(
    model_configs: List[Dict[str, Any]],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel across different providers.
    
    Args:
        model_configs: List of dicts with 'provider', 'model', and 'name' keys
        messages: List of message dicts to send to each model
        
    Returns:
        Dict mapping display name to response dict (or None if failed)
    """
    tasks = []
    model_names = []
    
    for config in model_configs:
        provider = config['provider']
        model = config['model']
        name = config.get('name', model)
        
        tasks.append(query_model(provider, model, messages, timeout=300.0))
        model_names.append(name)
    
    responses = await asyncio.gather(*tasks)
    
    return {name: response for name, response in zip(model_names, responses)}