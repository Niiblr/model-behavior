"""OpenAI provider implementation."""

import httpx
from typing import List, Dict, Any, Optional
from . import Provider


class OpenAIProvider(Provider):
    """Provider for OpenAI API (ChatGPT)."""
    
    def __init__(self, api_key: str):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    async def query(
        self,
        model: str,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """Query a model via OpenAI API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                message = data['choices'][0]['message']
                
                return {
                    'content': message.get('content'),
                }
        
        except Exception as e:
            print(f"Error querying OpenAI model {model}: {e}")
            return None