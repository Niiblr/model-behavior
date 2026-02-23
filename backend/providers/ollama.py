"""Ollama provider implementation (local and cloud)."""

import httpx
from typing import List, Dict, Any, Optional
from . import Provider


class OllamaProvider(Provider):
    """Provider for Ollama (local or cloud)."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama provider.
        
        Args:
            api_key: Optional API key for Ollama Cloud (leave None for local)
            base_url: Base URL for Ollama API
                     - Local: "http://localhost:11434" (default)
                     - Cloud: "https://api.ollama.com"
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/chat"
        self.is_cloud = api_key is not None
    
    async def query(
        self,
        model: str,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """Query a model via Ollama API."""
        headers = {
            "Content-Type": "application/json",
        }
        
        # Add authorization header for cloud
        if self.is_cloud and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False  # We want the complete response
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
                
                # Ollama returns the message in a different format
                return {
                    'content': data['message']['content'],
                }
        
        except Exception as e:
            print(f"Error querying Ollama model {model}: {e}")
            return None