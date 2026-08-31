# app/core/redis.py

import redis
import json
import logging
from typing import Optional, Any, Union
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """
    🔥 Redis Service for caching and token storage
    Handles password reset tokens, session caching, etc.
    """

    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.client = None
        self._connect()

    def _connect(self):
        """Connect to Redis"""
        try:
            if not self.redis_url:
                logger.warning("⚠️ REDIS_URL not set. Redis disabled.")
                return

            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=10
            )
            # Test connection
            self.client.ping()
            logger.info("✅ Redis connected successfully")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {str(e)}")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Redis connection error: {str(e)}")
            self.client = None

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self.client is not None

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Set a value in Redis
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized if not string)
            expire: TTL in seconds (optional)
        
        Returns:
            bool: True if successful
        """
        if not self.is_connected():
            logger.warning("⚠️ Redis not connected. Set failed.")
            return False

        try:
            # Serialize value if not string
            if not isinstance(value, str):
                value = json.dumps(value)

            if expire:
                self.client.set(key, value, ex=expire)
            else:
                self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"❌ Redis set error for key '{key}': {str(e)}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis
        
        Args:
            key: Redis key
        
        Returns:
            Value or None if not found
        """
        if not self.is_connected():
            logger.warning("⚠️ Redis not connected. Get failed.")
            return None

        try:
            value = self.client.get(key)
            if value is None:
                return None

            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"❌ Redis get error for key '{key}': {str(e)}")
            return None

    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis
        
        Args:
            key: Redis key
        
        Returns:
            bool: True if successful
        """
        if not self.is_connected():
            return False

        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"❌ Redis delete error for key '{key}': {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis
        
        Args:
            key: Redis key
        
        Returns:
            bool: True if key exists
        """
        if not self.is_connected():
            return False

        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"❌ Redis exists error for key '{key}': {str(e)}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on a key
        
        Args:
            key: Redis key
            ttl: TTL in seconds
        
        Returns:
            bool: True if successful
        """
        if not self.is_connected():
            return False

        try:
            return self.client.expire(key, ttl)
        except Exception as e:
            logger.error(f"❌ Redis expire error for key '{key}': {str(e)}")
            return False

    # ============================================================
    # 🔥 PASSWORD RESET TOKEN METHODS
    # ============================================================

    def set_reset_token(self, token: str, user_id: int, expire: int = 3600) -> bool:
        """
        Store password reset token
        
        Args:
            token: Reset token
            user_id: User ID associated with token
            expire: TTL in seconds (default 1 hour)
        
        Returns:
            bool: True if successful
        """
        key = f"reset_token:{token}"
        return self.set(key, user_id, expire)

    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """
        Get user ID from reset token
        
        Args:
            token: Reset token
        
        Returns:
            int: User ID or None if not found
        """
        key = f"reset_token:{token}"
        return self.get(key)

    def delete_reset_token(self, token: str) -> bool:
        """
        Delete reset token
        
        Args:
            token: Reset token
        
        Returns:
            bool: True if successful
        """
        key = f"reset_token:{token}"
        return self.delete(key)

    def is_reset_token_valid(self, token: str) -> bool:
        """
        Check if reset token is valid
        
        Args:
            token: Reset token
        
        Returns:
            bool: True if token exists
        """
        key = f"reset_token:{token}"
        return self.exists(key)

    # ============================================================
    # 🔥 CACHE METHODS
    # ============================================================

    def cache_get(self, prefix: str, key: str) -> Optional[Any]:
        """Get cached value"""
        return self.get(f"{prefix}:{key}")

    def cache_set(self, prefix: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value"""
        if ttl is None:
            ttl = settings.REDIS_CACHE_TTL
        return self.set(f"{prefix}:{key}", value, ttl)

    def cache_delete(self, prefix: str, key: str) -> bool:
        """Delete cached value"""
        return self.delete(f"{prefix}:{key}")

    def cache_clear_prefix(self, prefix: str) -> bool:
        """
        Clear all cache keys with given prefix
        
        Args:
            prefix: Cache prefix
        
        Returns:
            bool: True if successful
        """
        if not self.is_connected():
            return False

        try:
            pattern = f"{prefix}:*"
            cursor = 0
            while True:
                cursor, keys = self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    self.client.delete(*keys)
                if cursor == 0:
                    break
            return True
        except Exception as e:
            logger.error(f"❌ Redis clear prefix error: {str(e)}")
            return False


# ============================================================
# 🔥 SINGLETON INSTANCE
# ============================================================
redis_service = RedisService()