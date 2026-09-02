# app/core/redis.py
# 🔥 REDIS IMEFUNGWA KWA SASA - KUTOKANA NA MATATIZO YA CONNECTION
# 🔥 ITAFUNGULIWA TENA BAADA YA KUTATUA

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
    
    ⚠️ REDIS IMEFUNGWA KWA SASA - HAIJATUMIKA
    """

    def __init__(self):
        # 🔥 REDIS IMEFUNGWA - HAIJAITWA
        self.redis_url = None  # settings.REDIS_URL - IMEFUNGWA
        self.client = None
        # self._connect()  # 🔥 IMEFUNGWA
        logger.info("⚠️ Redis is DISABLED - Using fallback mode")

    def _connect(self):
        """🔴 IMEFUNGWA - Connect to Redis"""
        # try:
        #     if not self.redis_url:
        #         logger.warning("⚠️ REDIS_URL not set. Redis disabled.")
        #         return
        #
        #     self.client = redis.from_url(
        #         self.redis_url,
        #         decode_responses=True,
        #         socket_connect_timeout=5,
        #         socket_timeout=5,
        #         retry_on_timeout=True,
        #         max_connections=10
        #     )
        #     # Test connection
        #     self.client.ping()
        #     logger.info("✅ Redis connected successfully")
        # except redis.exceptions.ConnectionError as e:
        #     logger.error(f"❌ Redis connection failed: {str(e)}")
        #     self.client = None
        # except Exception as e:
        #     logger.error(f"❌ Redis connection error: {str(e)}")
        #     self.client = None
        logger.info("ℹ️ Redis _connect() skipped - Redis is disabled")

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        # 🔥 KWA SASA DAIMA INARUDISHA False
        return False
        # return self.client is not None

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Set a value in Redis
        🔥 IMEFUNGWA - DAIMA INARUDISHA True (Ili kuzuia errors)
        """
        # if not self.is_connected():
        #     logger.warning("⚠️ Redis not connected. Set failed.")
        #     return False
        #
        # try:
        #     # Serialize value if not string
        #     if not isinstance(value, str):
        #         value = json.dumps(value)
        #
        #     if expire:
        #         self.client.set(key, value, ex=expire)
        #     else:
        #         self.client.set(key, value)
        #     return True
        # except Exception as e:
        #     logger.error(f"❌ Redis set error for key '{key}': {str(e)}")
        #     return False
        
        # 🔥 FALLBACK - DAIMA SUCCESS (BILA REDIS)
        logger.debug(f"ℹ️ Redis SET bypassed (disabled): {key}")
        return True

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis
        🔥 IMEFUNGWA - DAIMA INARUDISHA None
        """
        # if not self.is_connected():
        #     logger.warning("⚠️ Redis not connected. Get failed.")
        #     return None
        #
        # try:
        #     value = self.client.get(key)
        #     if value is None:
        #         return None
        #
        #     # Try to deserialize JSON
        #     try:
        #         return json.loads(value)
        #     except (json.JSONDecodeError, TypeError):
        #         return value
        # except Exception as e:
        #     logger.error(f"❌ Redis get error for key '{key}': {str(e)}")
        #     return None
        
        # 🔥 FALLBACK - DAIMA INARUDISHA None
        logger.debug(f"ℹ️ Redis GET bypassed (disabled): {key}")
        return None

    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis
        🔥 IMEFUNGWA - DAIMA INARUDISHA True
        """
        # if not self.is_connected():
        #     return False
        #
        # try:
        #     self.client.delete(key)
        #     return True
        # except Exception as e:
        #     logger.error(f"❌ Redis delete error for key '{key}': {str(e)}")
        #     return False
        
        logger.debug(f"ℹ️ Redis DELETE bypassed (disabled): {key}")
        return True

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis
        🔥 IMEFUNGWA - DAIMA INARUDISHA False
        """
        # if not self.is_connected():
        #     return False
        #
        # try:
        #     return self.client.exists(key) > 0
        # except Exception as e:
        #     logger.error(f"❌ Redis exists error for key '{key}': {str(e)}")
        #     return False
        
        logger.debug(f"ℹ️ Redis EXISTS bypassed (disabled): {key}")
        return False

    def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on a key
        🔥 IMEFUNGWA - DAIMA INARUDISHA True
        """
        # if not self.is_connected():
        #     return False
        #
        # try:
        #     return self.client.expire(key, ttl)
        # except Exception as e:
        #     logger.error(f"❌ Redis expire error for key '{key}': {str(e)}")
        #     return False
        
        logger.debug(f"ℹ️ Redis EXPIRE bypassed (disabled): {key}")
        return True

    # ============================================================
    # 🔥 PASSWORD RESET TOKEN METHODS - IMEFUNGWA
    # ============================================================

    def set_reset_token(self, token: str, user_id: int, expire: int = 3600) -> bool:
        """
        Store password reset token
        🔥 IMEFUNGWA - DAIMA INARUDISHA True
        """
        # key = f"reset_token:{token}"
        # return self.set(key, user_id, expire)
        logger.debug(f"ℹ️ Redis SET_RESET_TOKEN bypassed (disabled): {token}")
        return True

    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """
        Get user ID from reset token
        🔥 IMEFUNGWA - DAIMA INARUDISHA None
        """
        # key = f"reset_token:{token}"
        # return self.get(key)
        logger.debug(f"ℹ️ Redis GET_USER_ID_FROM_TOKEN bypassed (disabled): {token}")
        return None

    def delete_reset_token(self, token: str) -> bool:
        """
        Delete reset token
        🔥 IMEFUNGWA - DAIMA INARUDISHA True
        """
        # key = f"reset_token:{token}"
        # return self.delete(key)
        logger.debug(f"ℹ️ Redis DELETE_RESET_TOKEN bypassed (disabled): {token}")
        return True

    def is_reset_token_valid(self, token: str) -> bool:
        """
        Check if reset token is valid
        🔥 IMEFUNGWA - DAIMA INARUDISHA False
        """
        # key = f"reset_token:{token}"
        # return self.exists(key)
        logger.debug(f"ℹ️ Redis IS_RESET_TOKEN_VALID bypassed (disabled): {token}")
        return False

    # ============================================================
    # 🔥 CACHE METHODS - IMEFUNGWA
    # ============================================================

    def cache_get(self, prefix: str, key: str) -> Optional[Any]:
        """Get cached value - IMEFUNGWA"""
        # return self.get(f"{prefix}:{key}")
        logger.debug(f"ℹ️ Redis CACHE_GET bypassed (disabled): {prefix}:{key}")
        return None

    def cache_set(self, prefix: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value - IMEFUNGWA"""
        # if ttl is None:
        #     ttl = settings.REDIS_CACHE_TTL
        # return self.set(f"{prefix}:{key}", value, ttl)
        logger.debug(f"ℹ️ Redis CACHE_SET bypassed (disabled): {prefix}:{key}")
        return True

    def cache_delete(self, prefix: str, key: str) -> bool:
        """Delete cached value - IMEFUNGWA"""
        # return self.delete(f"{prefix}:{key}")
        logger.debug(f"ℹ️ Redis CACHE_DELETE bypassed (disabled): {prefix}:{key}")
        return True

    def cache_clear_prefix(self, prefix: str) -> bool:
        """
        Clear all cache keys with given prefix - IMEFUNGWA
        """
        # if not self.is_connected():
        #     return False
        #
        # try:
        #     pattern = f"{prefix}:*"
        #     cursor = 0
        #     while True:
        #         cursor, keys = self.client.scan(cursor, match=pattern, count=100)
        #         if keys:
        #             self.client.delete(*keys)
        #         if cursor == 0:
        #             break
        #     return True
        # except Exception as e:
        #     logger.error(f"❌ Redis clear prefix error: {str(e)}")
        #     return False
        
        logger.debug(f"ℹ️ Redis CACHE_CLEAR_PREFIX bypassed (disabled): {prefix}")
        return True


# ============================================================
# 🔥 SINGLETON INSTANCE - BADO INAUNDWA LAKINI IMEFUNGWA
# ============================================================
redis_service = RedisService()

# ✅ LOG YA KUONYESHA KWAMBA REDIS IMEFUNGWA
logger.info("✅ RedisService initialized in DISABLED mode")