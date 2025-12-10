"""
Caching utilities for parsed resumes, JD, and intermediate results.
"""

import hashlib
import json
import pickle
import os
from pathlib import Path
from typing import Any, Optional, Dict
from functools import wraps
import time


# ==================== File-based Cache ====================

class FileCache:
    """Simple file-based cache with hash-based keys.
    
    Gracefully handles failures (e.g., on Streamlit Cloud with ephemeral storage).
    If caching fails, operations continue without caching.
    """
    
    def __init__(self, cache_dir: Path = Path(".cache")):
        self.cache_dir = Path(cache_dir)
        self.enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        
        # Try to create cache directory, but don't fail if it doesn't work
        if self.enabled:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                # On Streamlit Cloud or read-only filesystems, caching will be disabled
                print(f"⚠️ Cache directory creation failed: {e}. Caching disabled.")
                self.enabled = False
    
    def _get_cache_key(self, data: Any) -> str:
        """Generate cache key from data."""
        if isinstance(data, str):
            content = data
        elif isinstance(data, (dict, list)):
            content = json.dumps(data, sort_keys=True)
        else:
            content = str(data)
        
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, key: str, suffix: str = ".pkl") -> Path:
        """Get cache file path for key."""
        return self.cache_dir / f"{key}{suffix}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        if not self.enabled:
            return None
            
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"⚠️ Cache read error for {key}: {e}")
                return None
        return None
    
    def set(self, key: str, value: Any):
        """Set cached value. Fails silently if caching is disabled or unavailable."""
        if not self.enabled:
            return
            
        cache_path = self._get_cache_path(key)
        try:
            # Ensure parent directory exists
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
        except (OSError, PermissionError, Exception) as e:
            # Silently fail on Streamlit Cloud or read-only filesystems
            # This is expected behavior for ephemeral storage
            pass
    
    def get_or_compute(self, key: str, compute_func: callable, *args, **kwargs) -> Any:
        """Get from cache or compute and cache."""
        cached = self.get(key)
        if cached is not None:
            return cached
        
        result = compute_func(*args, **kwargs)
        self.set(key, result)
        return result
    
    def clear(self, pattern: Optional[str] = None):
        """Clear cache files."""
        if pattern:
            for cache_file in self.cache_dir.glob(pattern):
                cache_file.unlink()
        else:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()


# Global cache instances
resume_cache = FileCache(Path(".cache/resumes"))
jd_cache = FileCache(Path(".cache/jd"))
score_cache = FileCache(Path(".cache/scores"))


# ==================== Decorator-based Caching ====================

def cached(cache_instance: FileCache, key_func: Optional[callable] = None):
    """
    Decorator for caching function results.
    
    Args:
        cache_instance: FileCache instance to use
        key_func: Function to generate cache key from args/kwargs
    """
    def decorator(func: callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use function name + args hash
                key_data = (func.__name__, str(args), str(sorted(kwargs.items())))
                cache_key = hashlib.md5(str(key_data).encode()).hexdigest()
            
            # Try cache first
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache_instance.set(cache_key, result)
            return result
        
        return wrapper
    return decorator


# ==================== Resume-specific Caching ====================

def get_resume_cache_key(resume_path: Path) -> str:
    """Generate cache key for resume file based on content hash."""
    try:
        with open(resume_path, 'rb') as f:
            content = f.read()
        return hashlib.md5(content).hexdigest()
    except Exception:
        # Fallback to filename hash
        return hashlib.md5(str(resume_path).encode()).hexdigest()


def get_jd_cache_key(jd_path: Path) -> str:
    """Generate cache key for JD file based on content hash."""
    try:
        with open(jd_path, 'rb') as f:
            content = f.read()
        return hashlib.md5(content).hexdigest()
    except Exception:
        return hashlib.md5(str(jd_path).encode()).hexdigest()

