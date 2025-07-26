"""
Command Result Caching for AUX Protocol.

This module provides intelligent caching of command results to improve
performance for repeated operations and reduce browser overhead.
"""

import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class Cacheability(Enum):
    """Determines if a command result can be cached."""
    CACHEABLE = "cacheable"           # Safe to cache and reuse
    INVALIDATES = "invalidates"       # Command invalidates cached data
    NOT_CACHEABLE = "not_cacheable"   # Should never be cached


@dataclass
class CacheEntry:
    """Represents a cached command result."""
    
    key: str
    command_hash: str
    result: Dict[str, Any]
    timestamp: float
    access_count: int = 0
    last_accessed: float = 0.0
    ttl_seconds: int = 300  # 5 minutes default
    page_state_hash: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.timestamp > self.ttl_seconds
    
    def touch(self) -> None:
        """Update access tracking."""
        self.access_count += 1
        self.last_accessed = time.time()


class CommandCache:
    """
    Intelligent command result cache for AUX Protocol.
    
    Caches results of read-only operations and invalidates cache
    when page state changes occur.
    """
    
    # Commands that are safe to cache (read-only operations)
    CACHEABLE_COMMANDS = {
        'extract': Cacheability.CACHEABLE,
        'wait': Cacheability.CACHEABLE,  # Only for existence checks
    }
    
    # Commands that invalidate cache (state-changing operations)
    INVALIDATING_COMMANDS = {
        'navigate': Cacheability.INVALIDATES,
        'click': Cacheability.INVALIDATES,
        'fill': Cacheability.INVALIDATES,
    }
    
    def __init__(self, 
                 max_entries: int = 1000,
                 default_ttl: int = 300,
                 enable_page_state_tracking: bool = True):
        """
        Initialize command cache.
        
        Args:
            max_entries: Maximum number of cache entries
            default_ttl: Default TTL for cache entries in seconds
            enable_page_state_tracking: Enable page state change detection
        """
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.enable_page_state_tracking = enable_page_state_tracking
        
        # Cache storage
        self.cache: Dict[str, CacheEntry] = {}
        self.session_page_states: Dict[str, str] = {}  # session_id -> page_state_hash
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'evictions': 0,
            'total_requests': 0
        }
    
    def _hash_command(self, command_data: Dict[str, Any]) -> str:
        """
        Create a hash of command data for cache key generation.
        
        Args:
            command_data: Command data dictionary
            
        Returns:
            Command hash string
        """
        # Create a normalized version for hashing
        cache_data = {
            'method': command_data.get('method'),
            'selector': command_data.get('selector'),
            'url': str(command_data.get('url', '')),
            'extract_type': command_data.get('extract_type'),
            'attribute_name': command_data.get('attribute_name'),
            'property_name': command_data.get('property_name'),
            'condition': command_data.get('condition'),
            'text_content': command_data.get('text_content'),
            'multiple': command_data.get('multiple', False),
            'trim_whitespace': command_data.get('trim_whitespace', True),
        }
        
        # Remove None values and sort for consistent hashing
        filtered_data = {k: v for k, v in cache_data.items() if v is not None}
        normalized_json = json.dumps(filtered_data, sort_keys=True)
        
        return hashlib.sha256(normalized_json.encode()).hexdigest()[:16]
    
    def _generate_cache_key(self, session_id: str, command_hash: str) -> str:
        """Generate cache key for command."""
        return f"{session_id}:{command_hash}"
    
    def _get_page_state_hash(self, session_id: str, page_url: str, page_title: str) -> str:
        """
        Generate page state hash for invalidation detection.
        
        Args:
            session_id: Browser session ID
            page_url: Current page URL
            page_title: Current page title
            
        Returns:
            Page state hash
        """
        state_data = {
            'url': page_url,
            'title': page_title,
            'timestamp': int(time.time() / 60)  # Round to minute for stability
        }
        
        state_json = json.dumps(state_data, sort_keys=True)
        return hashlib.sha256(state_json.encode()).hexdigest()[:12]
    
    def can_cache_command(self, command_data: Dict[str, Any]) -> Cacheability:
        """
        Determine if a command result can be cached.
        
        Args:
            command_data: Command data dictionary
            
        Returns:
            Cacheability enum value
        """
        method = command_data.get('method', '').lower()
        
        # Check if command is in cacheable list
        if method in self.CACHEABLE_COMMANDS:
            # Additional checks for specific commands
            if method == 'wait':
                # Only cache existence/visibility checks, not custom JS
                condition = command_data.get('condition', '').lower()
                has_custom_js = command_data.get('custom_js')
                if has_custom_js or condition not in ['visible', 'hidden', 'attached', 'detached']:
                    return Cacheability.NOT_CACHEABLE
            
            return self.CACHEABLE_COMMANDS[method]
        
        # Check if command invalidates cache
        if method in self.INVALIDATING_COMMANDS:
            return self.INVALIDATING_COMMANDS[method]
        
        return Cacheability.NOT_CACHEABLE
    
    async def get_cached_result(self, 
                               session_id: str, 
                               command_data: Dict[str, Any],
                               current_page_url: str = "",
                               current_page_title: str = "") -> Optional[Dict[str, Any]]:
        """
        Retrieve cached result for command if available and valid.
        
        Args:
            session_id: Browser session ID
            command_data: Command data dictionary
            current_page_url: Current page URL for state validation
            current_page_title: Current page title for state validation
            
        Returns:
            Cached result if available, None otherwise
        """
        self.stats['total_requests'] += 1
        
        # Check if command is cacheable
        cacheability = self.can_cache_command(command_data)
        if cacheability != Cacheability.CACHEABLE:
            return None
        
        # Generate cache key
        command_hash = self._hash_command(command_data)
        cache_key = self._generate_cache_key(session_id, command_hash)
        
        # Check if entry exists
        if cache_key not in self.cache:
            self.stats['misses'] += 1
            return None
        
        entry = self.cache[cache_key]
        
        # Check if entry is expired
        if entry.is_expired():
            del self.cache[cache_key]
            self.stats['misses'] += 1
            return None
        
        # Check page state if enabled
        if self.enable_page_state_tracking and current_page_url:
            current_state_hash = self._get_page_state_hash(
                session_id, current_page_url, current_page_title
            )
            
            if entry.page_state_hash and entry.page_state_hash != current_state_hash:
                # Page state changed, invalidate entry
                del self.cache[cache_key]
                self.stats['invalidations'] += 1
                self.stats['misses'] += 1
                return None
        
        # Valid cache hit
        entry.touch()
        self.stats['hits'] += 1
        
        logger.debug(f"Cache hit for {command_data.get('method')} command")
        return entry.result.copy()
    
    async def cache_result(self, 
                          session_id: str, 
                          command_data: Dict[str, Any],
                          result: Dict[str, Any],
                          current_page_url: str = "",
                          current_page_title: str = "",
                          custom_ttl: Optional[int] = None) -> None:
        """
        Cache command result if cacheable.
        
        Args:
            session_id: Browser session ID
            command_data: Command data dictionary
            result: Command result to cache
            current_page_url: Current page URL for state tracking
            current_page_title: Current page title for state tracking
            custom_ttl: Custom TTL override for this entry
        """
        # Check if command is cacheable
        cacheability = self.can_cache_command(command_data)
        if cacheability != Cacheability.CACHEABLE:
            return
        
        # Only cache successful results
        if not result.get('success', False):
            return
        
        # Generate cache key
        command_hash = self._hash_command(command_data)
        cache_key = self._generate_cache_key(session_id, command_hash)
        
        # Generate page state hash if enabled
        page_state_hash = None
        if self.enable_page_state_tracking and current_page_url:
            page_state_hash = self._get_page_state_hash(
                session_id, current_page_url, current_page_title
            )
            self.session_page_states[session_id] = page_state_hash
        
        # Create cache entry
        entry = CacheEntry(
            key=cache_key,
            command_hash=command_hash,
            result=result.copy(),
            timestamp=time.time(),
            ttl_seconds=custom_ttl or self.default_ttl,
            page_state_hash=page_state_hash
        )
        
        # Check if cache is full and evict if necessary
        if len(self.cache) >= self.max_entries:
            await self._evict_oldest_entries()
        
        self.cache[cache_key] = entry
        logger.debug(f"Cached result for {command_data.get('method')} command")
    
    async def invalidate_session(self, session_id: str) -> None:
        """
        Invalidate all cache entries for a session.
        
        Args:
            session_id: Browser session ID to invalidate
        """
        # Find and remove entries for this session
        keys_to_remove = [
            key for key in self.cache.keys() 
            if key.startswith(f"{session_id}:")
        ]
        
        for key in keys_to_remove:
            del self.cache[key]
        
        # Remove page state tracking
        self.session_page_states.pop(session_id, None)
        
        if keys_to_remove:
            self.stats['invalidations'] += len(keys_to_remove)
            logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for session {session_id}")
    
    async def invalidate_on_command(self, session_id: str, command_data: Dict[str, Any]) -> None:
        """
        Invalidate cache entries based on command type.
        
        Args:
            session_id: Browser session ID
            command_data: Command data that might invalidate cache
        """
        cacheability = self.can_cache_command(command_data)
        
        if cacheability == Cacheability.INVALIDATES:
            method = command_data.get('method', '').lower()
            
            if method == 'navigate':
                # Navigation invalidates all session cache
                await self.invalidate_session(session_id)
            elif method in ['click', 'fill']:
                # Interactive commands invalidate cache entries that might be affected
                await self._invalidate_interactive_command(session_id, command_data)
    
    async def _invalidate_interactive_command(self, session_id: str, command_data: Dict[str, Any]) -> None:
        """
        Invalidate cache entries that might be affected by interactive commands.
        
        Args:
            session_id: Browser session ID
            command_data: Interactive command data
        """
        # For simplicity, invalidate all extract commands for the session
        # In a more sophisticated implementation, could analyze selectors to
        # determine which cached extractions might be affected
        keys_to_remove = []
        
        for key, entry in self.cache.items():
            if key.startswith(f"{session_id}:"):
                # For interactive commands, invalidate all cached extractions
                # since they might be affected by the state change
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
        
        if keys_to_remove:
            self.stats['invalidations'] += len(keys_to_remove)
            logger.debug(f"Invalidated {len(keys_to_remove)} extract cache entries due to {command_data.get('method')} command")
    
    async def _evict_oldest_entries(self, count: int = None) -> None:
        """
        Evict oldest cache entries to make room.
        
        Args:
            count: Number of entries to evict (default: 10% of max_entries)
        """
        if count is None:
            count = max(1, self.max_entries // 10)
        
        # Sort entries by last accessed time (LRU eviction)
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].last_accessed or x[1].timestamp
        )
        
        # Remove oldest entries
        for i in range(min(count, len(sorted_entries))):
            key = sorted_entries[i][0]
            del self.cache[key]
            self.stats['evictions'] += 1
        
        logger.debug(f"Evicted {count} cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats['total_requests']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            'hit_rate_percent': round(hit_rate, 2),
            'cache_size': len(self.cache),
            'max_entries': self.max_entries,
            'memory_usage_estimate': len(self.cache) * 1024,  # Rough estimate
        }
    
    async def cleanup_expired_entries(self) -> int:
        """
        Clean up expired cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry.timestamp > entry.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.session_page_states.clear()
        logger.info("Cache cleared")


# Global cache instance
_command_cache: Optional[CommandCache] = None


def get_command_cache() -> CommandCache:
    """Get global command cache instance."""
    global _command_cache
    if _command_cache is None:
        _command_cache = CommandCache()
    return _command_cache


def init_command_cache(max_entries: int = 1000, default_ttl: int = 300) -> CommandCache:
    """
    Initialize global command cache.
    
    Args:
        max_entries: Maximum number of cache entries
        default_ttl: Default TTL in seconds
        
    Returns:
        Initialized command cache
    """
    global _command_cache
    _command_cache = CommandCache(max_entries=max_entries, default_ttl=default_ttl)
    return _command_cache