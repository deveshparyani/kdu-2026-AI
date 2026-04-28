"""Vision API integration with caching."""

import base64
from typing import Optional

from openai import OpenAI

from ..cache.vision_cache import VisionCache
from ..config import Config
from ..cost_tracker import CostTracker

# Global cache instance
_vision_cache = VisionCache(max_size=1000)


def call_vision_api(
    image_bytes: bytes,
    prompt: str,
    file_id: str,
    cost_tracker: CostTracker,
    openai_client: Optional[OpenAI] = None
) -> str:
    """Call GPT-4o-mini vision API with caching.
    
    Args:
        image_bytes: Image data as bytes
        prompt: Prompt for the vision model
        file_id: ID of the file being processed
        cost_tracker: CostTracker instance
        openai_client: OpenAI client (creates new if None)
        
    Returns:
        Description text from vision API
    """
    # Generate cache key from image hash
    cache_key = _vision_cache.get_image_hash(image_bytes)
    
    # Check cache first
    cached_result = _vision_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Create OpenAI client if not provided
    if openai_client is None:
        openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    # Encode image as base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # Call vision API
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=500
    )
    
    # Extract response text
    description = response.choices[0].message.content
    
    # Log cost
    cost_tracker.log_api_call(
        model="gpt-4o-mini",
        operation="vision",
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        file_id=file_id
    )
    
    # Store in cache
    _vision_cache.set(cache_key, description, ttl=Config.CACHE_TTL_SECONDS)
    
    return description


def clear_vision_cache() -> None:
    """Clear the vision API cache."""
    _vision_cache.clear()


def get_cache_size() -> int:
    """Get number of cached entries."""
    return _vision_cache.size()
