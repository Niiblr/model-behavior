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
        timeout: float = 120.0
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
                "maxOutputTokens": 8192,
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
                
                # Extract content from Gemini response format
                content = data['candidates'][0]['content']['parts'][0]['text']
                
                return {
                    'content': content,
                }
        
        except Exception as e:
            print(f"Error querying Gemini model {model}: {e}")
            return None