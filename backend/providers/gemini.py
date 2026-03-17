"""Google Gemini provider implementation."""

import httpx
from typing import List, Dict, Any, Optional
from . import Provider


class GeminiProvider(Provider):
    """Provider for Google Gemini API."""
    
    def __init__(self, api_key: str):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google AI Studio API key
        """
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    async def query(
        self,
        model: str,
        messages: List[Dict[str, str]],
        timeout: float = 120.0,
        max_tokens: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Query a model via Gemini API."""
        
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        # Gemini API endpoint
        api_url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 1.0,
                "maxOutputTokens": max_tokens if max_tokens is not None else 8192,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    api_url,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Safely extract content from Gemini response format
                candidates = data.get('candidates', [])
                if not candidates:
                    print(f"Gemini model {model}: no candidates in response: {data}")
                    return None
                content_obj = candidates[0].get('content', {})
                parts = content_obj.get('parts', [])
                if not parts:
                    print(f"Gemini model {model}: no parts in response: {data}")
                    return None
                content = parts[0].get('text', '')
                
                return {
                    'content': content,
                }
        
        except Exception as e:
            print(f"Error querying Gemini model {model}: {e}")
            return None