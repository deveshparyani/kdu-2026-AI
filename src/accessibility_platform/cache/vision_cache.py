"""Vision API caching using SHA-256 hashing and LRU cache."""

import hashlib
import time
from functools import lru_cache
from typing import Optional


class VisionCache:
    """In-memory LRU cache for vision API results."""
    
    def __init__(self, max_size: int = 1000):
        """Initialize cache with maximum size."""
        self._cache: dict[str, tuple[str, float]] = {}  # {key: (value, expiry_time)}
        self._max_size = max_size
    
    def get_image_hash(self, image_bytes: bytes) -> str:
        """Generate SHA-256 hash of image bytes."""
        return hashlib.sha256(image_bytes).hexdigest()
    
    def get(self, cache_key: str) -> Optional[str]:
        """Get cached value if exists and not expired."""
        if cache_key not in self._cache:
            return None
        
        value, expiry_time = self._cache[cache_key]
        
        # Check if expired
        if time.time() > expiry_time:
            del self._cache[cache_key]
            return None
        
        return value
    
    def set(self, cache_key: str, value: str, ttl: int) -> None:
        """Store value in cache with TTL in seconds."""
        # Implement simple LRU: remove oldest if at capacity
        if len(self._cache) >= self._max_size:
            # Remove the first (oldest) item
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        expiry_time = time.time() + ttl
        self._cache[cache_key] = (value, expiry_time)
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
    
    def size(self) -> int:
        """Return number of cached entries."""
        return len(self._cache)
    
    def __len__(self) -> int:
        """Return number of cached entries."""
        return len(self._cache)
