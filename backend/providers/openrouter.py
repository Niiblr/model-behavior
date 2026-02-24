""""OpenRouter provider implementation."""

import asyncio
import httpx
from typing import List, Dict, Any, Optional
from . import Provider

MAX_RETRIES = 4
BASE_DELAY = 5  # seconds


class OpenRouterProvider(Provider):
    """Provider for OpenRouter API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    async def query(
        self,
        model: str,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """Query a model via OpenRouter API with exponential backoff on rate limits."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
        }

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        self.api_url,
                        headers=headers,
                        json=payload
                    )

                    # Handle rate limiting with exponential backoff
                    if response.status_code == 429:
                        delay = BASE_DELAY * (2 ** attempt)
                        print(f"OpenRouter rate limit hit for {model}. Retrying in {delay}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                        await asyncio.sleep(delay)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    # Guard against unexpected response shapes
                    if 'choices' not in data or not data['choices']:
                        print(f"Unexpected response from OpenRouter for {model}: {data}")
                        return None

                    message = data['choices'][0]['message']
                    return {'content': message.get('content')}

            except httpx.HTTPStatusError as e:
                print(f"HTTP error querying OpenRouter model {model}: {e}")
                return None
            except Exception as e:
                print(f"Error querying OpenRouter model {model}: {e}")
                return None

        print(f"OpenRouter model {model} failed after {MAX_RETRIES} retries.")
        return None