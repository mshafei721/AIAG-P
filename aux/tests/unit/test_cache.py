"""
Comprehensive unit tests for AUX Protocol cache management.

Tests cover cache operations, expiration, memory management,
and performance characteristics of the caching system.
"""

import asyncio
import time
import pytest
from typing import Any, Dict
from unittest.mock import Mock, patch

from aux.cache import (
    CacheManager,
    CacheEntry,
    CacheConfig,
    InMemoryCache,
    LRUCache,
    TTLCache,
    CacheStats,
    cache_key_generator,
    serialize_cache_value,
    deserialize_cache_value,
)


class TestCacheEntry:
    """Test CacheEntry functionality."""
    
    def test_cache_entry_creation(self):
        """Test creation of cache entry."""
        entry = CacheEntry(
            key="test_key",
            value={"data": "test"},
            ttl=300,
            created_at=time.time()
        )
        assert entry.key == "test_key"
        assert entry.value["data"] == "test"
        assert entry.ttl == 300
        assert entry.created_at > 0
        
    def test_cache_entry_is_expired(self):
        """Test cache entry expiration check."""
        now = time.time()
        
        # Non-expired entry
        entry = CacheEntry(
            key="test",
            value="data",
            ttl=300,
            created_at=now
        )
        assert not entry.is_expired()
        
        # Expired entry
        expired_entry = CacheEntry(
            key="test",
            value="data",
            ttl=1,
            created_at=now - 2
        )
        assert expired_entry.is_expired()
        
    def test_cache_entry_no_ttl(self):
        """Test cache entry without TTL (never expires)."""
        entry = CacheEntry(
            key="test",
            value="data",
            ttl=None,
            created_at=time.time() - 1000
        )
        assert not entry.is_expired()
        
    def test_cache_entry_access_time_update(self):
        """Test cache entry access time update."""
        entry = CacheEntry(
            key="test",
            value="data",
            ttl=300,
            created_at=time.time()
        )
        
        original_access_time = entry.last_accessed
        time.sleep(0.01)  # Small delay
        entry.mark_accessed()
        
        assert entry.last_accessed > original_access_time
        assert entry.access_count == 2  # Created + accessed


class TestCacheConfig:
    """Test CacheConfig validation and functionality."""
    
    def test_valid_cache_config(self):
        """Test creation of valid cache configuration."""
        config = CacheConfig(
            max_size=1000,
            default_ttl=300,
            cleanup_interval=60,
            enable_stats=True
        )
        assert config.max_size == 1000
        assert config.default_ttl == 300
        assert config.cleanup_interval == 60
        assert config.enable_stats is True
        
    def test_cache_config_defaults(self):
        """Test cache configuration with default values."""
        config = CacheConfig()
        assert config.max_size == 1000
        assert config.default_ttl == 300
        assert config.cleanup_interval == 60
        assert config.enable_stats is True
        
    def test_cache_config_invalid_values(self):
        """Test cache configuration with invalid values."""
        with pytest.raises(ValueError):
            CacheConfig(max_size=0)
            
        with pytest.raises(ValueError):
            CacheConfig(default_ttl=-1)
            
        with pytest.raises(ValueError):
            CacheConfig(cleanup_interval=0)


class TestInMemoryCache:
    """Test InMemoryCache implementation."""
    
    @pytest.fixture
    def cache(self):
        """Provide a fresh cache instance for each test."""
        return InMemoryCache(CacheConfig(max_size=100, default_ttl=300))
        
    def test_cache_set_get(self, cache):
        """Test basic cache set and get operations."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
    def test_cache_set_with_custom_ttl(self, cache):
        """Test cache set with custom TTL."""
        cache.set("key1", "value1", ttl=600)
        entry = cache._storage["key1"]
        assert entry.ttl == 600
        
    def test_cache_get_nonexistent_key(self, cache):
        """Test cache get for nonexistent key."""
        assert cache.get("nonexistent") is None
        assert cache.get("nonexistent", default="default") == "default"
        
    def test_cache_delete(self, cache):
        """Test cache delete operation."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.delete("key1")
        assert cache.get("key1") is None
        
    def test_cache_clear(self, cache):
        """Test cache clear operation."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert len(cache) == 2
        
        cache.clear()
        assert len(cache) == 0
        
    def test_cache_contains(self, cache):
        """Test cache contains operation."""
        cache.set("key1", "value1")
        assert "key1" in cache
        assert "nonexistent" not in cache
        
    def test_cache_keys(self, cache):
        """Test cache keys operation."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        keys = list(cache.keys())
        assert "key1" in keys
        assert "key2" in keys
        assert len(keys) == 2
        
    def test_cache_values(self, cache):
        """Test cache values operation."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        values = list(cache.values())
        assert "value1" in values
        assert "value2" in values
        assert len(values) == 2
        
    def test_cache_items(self, cache):
        """Test cache items operation."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        items = list(cache.items())
        assert ("key1", "value1") in items
        assert ("key2", "value2") in items
        assert len(items) == 2


class TestLRUCache:
    """Test LRU (Least Recently Used) cache implementation."""
    
    @pytest.fixture
    def lru_cache(self):
        """Provide a fresh LRU cache instance."""
        return LRUCache(CacheConfig(max_size=3, default_ttl=300))
        
    def test_lru_cache_eviction(self, lru_cache):
        """Test LRU cache eviction policy."""
        # Fill cache to capacity
        lru_cache.set("key1", "value1")
        lru_cache.set("key2", "value2")
        lru_cache.set("key3", "value3")
        assert len(lru_cache) == 3
        
        # Add one more item - should evict least recently used
        lru_cache.set("key4", "value4")
        assert len(lru_cache) == 3
        assert "key1" not in lru_cache  # Should be evicted
        assert "key4" in lru_cache
        
    def test_lru_cache_access_order(self, lru_cache):
        """Test LRU cache access order tracking."""
        lru_cache.set("key1", "value1")
        lru_cache.set("key2", "value2")
        lru_cache.set("key3", "value3")
        
        # Access key1 to make it most recently used
        lru_cache.get("key1")
        
        # Add new item - key2 should be evicted (least recently used)
        lru_cache.set("key4", "value4")
        assert "key2" not in lru_cache
        assert "key1" in lru_cache  # Should not be evicted
        
    def test_lru_cache_update_existing(self, lru_cache):
        """Test LRU cache behavior when updating existing keys."""
        lru_cache.set("key1", "value1")
        lru_cache.set("key2", "value2")
        lru_cache.set("key3", "value3")
        
        # Update existing key - should not trigger eviction
        lru_cache.set("key1", "updated_value1")
        assert len(lru_cache) == 3
        assert lru_cache.get("key1") == "updated_value1"


class TestTTLCache:
    """Test TTL (Time To Live) cache implementation."""
    
    @pytest.fixture
    def ttl_cache(self):
        """Provide a fresh TTL cache instance."""
        return TTLCache(CacheConfig(max_size=100, default_ttl=1))
        
    def test_ttl_cache_expiration(self, ttl_cache):
        """Test TTL cache expiration."""
        ttl_cache.set("key1", "value1", ttl=0.1)  # Expires in 100ms
        assert ttl_cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.2)
        assert ttl_cache.get("key1") is None
        
    def test_ttl_cache_cleanup(self, ttl_cache):
        """Test TTL cache automatic cleanup."""
        ttl_cache.set("key1", "value1", ttl=0.1)
        ttl_cache.set("key2", "value2", ttl=10)  # Long TTL
        
        # Wait for key1 to expire
        time.sleep(0.2)
        
        # Trigger cleanup
        ttl_cache._cleanup_expired()
        
        assert "key1" not in ttl_cache._storage
        assert "key2" in ttl_cache._storage
        
    def test_ttl_cache_no_expiration(self, ttl_cache):
        """Test TTL cache with no expiration (None TTL)."""
        ttl_cache.set("key1", "value1", ttl=None)
        
        # Wait longer than default TTL
        time.sleep(1.5)
        
        # Should still be present
        assert ttl_cache.get("key1") == "value1"


class TestCacheStats:
    """Test cache statistics functionality."""
    
    @pytest.fixture
    def cache_with_stats(self):
        """Provide a cache with statistics enabled."""
        return InMemoryCache(CacheConfig(enable_stats=True))
        
    def test_cache_hit_miss_stats(self, cache_with_stats):
        """Test cache hit and miss statistics."""
        cache = cache_with_stats
        
        # Miss
        cache.get("nonexistent")
        stats = cache.get_stats()
        assert stats.misses == 1
        assert stats.hits == 0
        
        # Set and hit
        cache.set("key1", "value1")
        cache.get("key1")
        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        
    def test_cache_operation_stats(self, cache_with_stats):
        """Test cache operation statistics."""
        cache = cache_with_stats
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.delete("key1")
        
        stats = cache.get_stats()
        assert stats.sets == 2
        assert stats.deletes == 1
        
    def test_cache_hit_ratio(self, cache_with_stats):
        """Test cache hit ratio calculation."""
        cache = cache_with_stats
        
        # 2 misses, 1 hit = 33.33% hit ratio
        cache.get("miss1")
        cache.get("miss2")
        cache.set("key1", "value1")
        cache.get("key1")
        
        stats = cache.get_stats()
        assert abs(stats.hit_ratio - 0.3333) < 0.001
        
    def test_cache_reset_stats(self, cache_with_stats):
        """Test cache statistics reset."""
        cache = cache_with_stats
        
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("nonexistent")
        
        stats = cache.get_stats()
        assert stats.hits > 0
        assert stats.misses > 0
        
        cache.reset_stats()
        stats = cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0


class TestCacheManager:
    """Test CacheManager high-level operations."""
    
    @pytest.fixture
    def cache_manager(self):
        """Provide a cache manager instance."""
        return CacheManager(CacheConfig(max_size=100, default_ttl=300))
        
    async def test_cache_manager_async_operations(self, cache_manager):
        """Test cache manager async operations."""
        await cache_manager.aset("key1", "value1")
        value = await cache_manager.aget("key1")
        assert value == "value1"
        
        await cache_manager.adelete("key1")
        value = await cache_manager.aget("key1")
        assert value is None
        
    async def test_cache_manager_batch_operations(self, cache_manager):
        """Test cache manager batch operations."""
        items = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        
        await cache_manager.aset_many(items)
        
        values = await cache_manager.aget_many(["key1", "key2", "key3"])
        assert values["key1"] == "value1"
        assert values["key2"] == "value2"
        assert values["key3"] == "value3"
        
    async def test_cache_manager_with_serialization(self, cache_manager):
        """Test cache manager with complex data serialization."""
        complex_data = {
            "list": [1, 2, 3],
            "dict": {"nested": True},
            "tuple": ("a", "b", "c")
        }
        
        await cache_manager.aset("complex", complex_data)
        retrieved = await cache_manager.aget("complex")
        
        assert retrieved["list"] == [1, 2, 3]
        assert retrieved["dict"]["nested"] is True
        assert retrieved["tuple"] == ("a", "b", "c")
        
    async def test_cache_manager_auto_cleanup(self, cache_manager):
        """Test cache manager automatic cleanup."""
        # Set items with short TTL
        await cache_manager.aset("short_lived", "value", ttl=0.1)
        await cache_manager.aset("long_lived", "value", ttl=10)
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Trigger cleanup
        await cache_manager.cleanup_expired()
        
        assert await cache_manager.aget("short_lived") is None
        assert await cache_manager.aget("long_lived") == "value"


class TestCacheUtilities:
    """Test cache utility functions."""
    
    def test_cache_key_generator(self):
        """Test cache key generation utility."""
        key1 = cache_key_generator("prefix", "arg1", "arg2", kwarg1="value1")
        key2 = cache_key_generator("prefix", "arg1", "arg2", kwarg1="value1")
        key3 = cache_key_generator("prefix", "arg1", "arg2", kwarg1="value2")
        
        assert key1 == key2  # Same args should produce same key
        assert key1 != key3  # Different args should produce different key
        
    def test_cache_serialization(self):
        """Test cache value serialization and deserialization."""
        original_data = {
            "string": "test",
            "number": 42,
            "list": [1, 2, 3],
            "dict": {"nested": True}
        }
        
        serialized = serialize_cache_value(original_data)
        deserialized = deserialize_cache_value(serialized)
        
        assert deserialized == original_data
        
    def test_cache_serialization_edge_cases(self):
        """Test cache serialization with edge cases."""
        test_cases = [
            None,
            "",
            0,
            [],
            {},
            "unicode_test_测试"
        ]
        
        for test_case in test_cases:
            serialized = serialize_cache_value(test_case)
            deserialized = deserialize_cache_value(serialized)
            assert deserialized == test_case


class TestCachePerformance:
    """Test cache performance characteristics."""
    
    @pytest.mark.performance
    def test_cache_performance_large_dataset(self):
        """Test cache performance with large dataset."""
        cache = InMemoryCache(CacheConfig(max_size=10000, enable_stats=True))
        
        # Measure set performance
        start_time = time.time()
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        set_time = time.time() - start_time
        
        # Measure get performance
        start_time = time.time()
        for i in range(1000):
            cache.get(f"key_{i}")
        get_time = time.time() - start_time
        
        # Performance assertions (adjust thresholds as needed)
        assert set_time < 1.0  # Should set 1000 items in less than 1 second
        assert get_time < 0.5  # Should get 1000 items in less than 0.5 seconds
        
        stats = cache.get_stats()
        assert stats.hits == 1000
        assert stats.hit_ratio == 1.0
        
    @pytest.mark.performance
    def test_cache_memory_usage(self):
        """Test cache memory usage characteristics."""
        import sys
        
        cache = InMemoryCache(CacheConfig(max_size=1000))
        
        # Measure initial memory
        initial_size = sys.getsizeof(cache._storage)
        
        # Add items
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}" * 100)  # Larger values
            
        # Measure final memory
        final_size = sys.getsizeof(cache._storage)
        
        # Memory should have increased but not excessively
        assert final_size > initial_size
        memory_per_item = (final_size - initial_size) / 100
        assert memory_per_item < 10000  # Reasonable memory per item


class TestCacheThreadSafety:
    """Test cache thread safety (if applicable)."""
    
    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self):
        """Test cache behavior under concurrent access."""
        cache = InMemoryCache(CacheConfig(max_size=1000))
        
        async def worker(worker_id: int):
            for i in range(100):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                cache.set(key, value)
                retrieved = cache.get(key)
                assert retrieved == value
                
        # Run multiple workers concurrently
        tasks = [worker(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Verify final state
        assert len(cache) == 1000  # 10 workers * 100 items each
        
    @pytest.mark.asyncio
    async def test_cache_concurrent_cleanup(self):
        """Test cache cleanup under concurrent access."""
        cache = TTLCache(CacheConfig(max_size=1000, default_ttl=0.1))
        
        async def setter():
            for i in range(100):
                cache.set(f"key_{i}", f"value_{i}", ttl=0.05)
                await asyncio.sleep(0.01)
                
        async def cleaner():
            for _ in range(10):
                await asyncio.sleep(0.02)
                cache._cleanup_expired()
                
        # Run setter and cleaner concurrently
        await asyncio.gather(setter(), cleaner())
        
        # Most items should be expired and cleaned up
        assert len(cache) < 50


class TestCacheErrorHandling:
    """Test cache error handling and edge cases."""
    
    def test_cache_invalid_key_types(self):
        """Test cache behavior with invalid key types."""
        cache = InMemoryCache(CacheConfig())
        
        # Test with unhashable keys
        with pytest.raises(TypeError):
            cache.set(["list", "key"], "value")
            
        with pytest.raises(TypeError):
            cache.set({"dict": "key"}, "value")
            
    def test_cache_serialization_errors(self):
        """Test cache behavior with non-serializable values."""
        cache = InMemoryCache(CacheConfig())
        
        # Test with non-serializable value (lambda function)
        non_serializable = lambda x: x
        
        # Cache should handle this gracefully
        cache.set("key", non_serializable)
        # Retrieving might return None or raise an error depending on implementation
        
    def test_cache_extreme_values(self):
        """Test cache with extreme values."""
        cache = InMemoryCache(CacheConfig(max_size=2))
        
        # Test with very large value
        large_value = "x" * 1000000  # 1MB string
        cache.set("large", large_value)
        assert cache.get("large") == large_value
        
        # Test with empty values
        cache.set("empty_string", "")
        cache.set("empty_list", [])
        cache.set("empty_dict", {})
        
        assert cache.get("empty_string") == ""
        assert cache.get("empty_list") == []
        assert cache.get("empty_dict") == {}
