"""
Simple in-memory cache for LLM responses based on input hash.
No expiration - cache lives for the duration of the process.
"""

import hashlib
import json
from typing import Any, Dict, Optional
from janito.llm.driver_input import DriverInput


class ResponseCache:
    """Simple in-memory cache for LLM responses with no expiration."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def _generate_key(self, driver_input: DriverInput) -> str:
        """Generate a cache key from driver input."""
        # Create a deterministic representation of the input
        cache_data = {
            "conversation_history": driver_input.conversation_history.get_history(),
            "config": {
                "model": getattr(driver_input.config, "model", None),
                "temperature": getattr(driver_input.config, "temperature", None),
                "max_tokens": getattr(driver_input.config, "max_tokens", None),
                "top_p": getattr(driver_input.config, "top_p", None),
                "presence_penalty": getattr(driver_input.config, "presence_penalty", None),
                "frequency_penalty": getattr(driver_input.config, "frequency_penalty", None),
                "stop": getattr(driver_input.config, "stop", None),
            }
        }
        
        # Create hash from JSON representation
        cache_str = json.dumps(cache_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(cache_str.encode('utf-8')).hexdigest()
    
    def get(self, driver_input: DriverInput) -> Optional[Any]:
        """Get cached response for the given input."""
        key = self._generate_key(driver_input)
        return self._cache.get(key)
    
    def set(self, driver_input: DriverInput, response: Any) -> None:
        """Cache the response for the given input."""
        key = self._generate_key(driver_input)
        self._cache[key] = response
    
    def clear(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "total_entries": len(self._cache),
            "total_size": sum(len(str(v)) for v in self._cache.values())
        }