"""
Redis service for multi-worker state sharing
Manages call session state across multiple Gunicorn workers
"""
import os
import json
import logging
from typing import Optional, Dict, Any
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

class RedisService:
    """Redis client for managing distributed call state"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection"""
        try:
            if not self.redis_url:
                logger.warning("⚠️ REDIS_URL not set - falling back to in-memory storage (not suitable for multi-worker)")
                return
            
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.client.ping()
            logger.info("✅ Redis connected successfully")
            
        except RedisError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.warning("⚠️ Falling back to in-memory storage (not suitable for multi-worker)")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to Redis: {e}")
            self.client = None
    
    def set_call_data(self, call_control_id: str, call_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Store call data in Redis with automatic expiration
        
        Args:
            call_control_id: Unique call identifier
            call_data: Dictionary containing agent, custom_variables, etc.
            ttl: Time-to-live in seconds (default 1 hour)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.warning(f"⚠️ Redis not available - cannot store call data for {call_control_id}")
            return False
        
        try:
            # Serialize call_data to JSON (only serializable data)
            # Note: We skip 'session' object as it's not serializable
            serializable_data = {
                "agent": call_data.get("agent"),
                "agent_id": call_data.get("agent_id"),  # CRITICAL: For cross-worker session recreation
                "user_id": call_data.get("user_id"),  # CRITICAL: For cross-worker session recreation
                "custom_variables": call_data.get("custom_variables", {}),
                "flow_type": call_data.get("flow_type"),
                "awaiting_speech": call_data.get("awaiting_speech", False),
                "last_agent_text": call_data.get("last_agent_text", ""),
                "processing_speech": call_data.get("processing_speech", False),
                "chunk_count": call_data.get("chunk_count", 0),
                "recent_agent_texts": call_data.get("recent_agent_texts", []),
                "user_has_spoken": call_data.get("user_has_spoken", False),  # CRITICAL: For Double Speaking protection
                "silence_greeting_triggered": call_data.get("silence_greeting_triggered", False)
            }
            
            key = f"call:{call_control_id}"
            self.client.setex(key, ttl, json.dumps(serializable_data))
            logger.info(f"📦 Stored call data in Redis: {call_control_id} (TTL: {ttl}s)")
            return True
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"❌ Failed to store call data in Redis: {e}")
            return False
    
    def get_call_data(self, call_control_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve call data from Redis
        
        Args:
            call_control_id: Unique call identifier
        
        Returns:
            Dictionary with call data, or None if not found
        """
        if not self.client:
            logger.warning(f"⚠️ Redis not available - cannot retrieve call data for {call_control_id}")
            return None
        
        try:
            key = f"call:{call_control_id}"
            data = self.client.get(key)
            
            if data:
                logger.info(f"📥 Retrieved call data from Redis: {call_control_id}")
                return json.loads(data)
            else:
                logger.warning(f"⚠️ Call data not found in Redis: {call_control_id}")
                return None
                
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"❌ Failed to retrieve call data from Redis: {e}")
            return None
    
    def update_call_data(self, call_control_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific fields in call data
        
        Args:
            call_control_id: Unique call identifier
            updates: Dictionary with fields to update
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Get existing data
            existing_data = self.get_call_data(call_control_id)
            if not existing_data:
                logger.warning(f"⚠️ Cannot update - call data not found: {call_control_id}")
                return False
            
            # Merge updates
            existing_data.update(updates)
            
            # Store back with same TTL
            return self.set_call_data(call_control_id, existing_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to update call data: {e}")
            return False
    
    def delete_call_data(self, call_control_id: str) -> bool:
        """
        Remove call data from Redis (cleanup)
        
        Args:
            call_control_id: Unique call identifier
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            key = f"call:{call_control_id}"
            result = self.client.delete(key)
            
            if result:
                logger.info(f"🧹 Deleted call data from Redis: {call_control_id}")
            else:
                logger.warning(f"⚠️ Call data not found for deletion: {call_control_id}")
            
            return bool(result)
            
        except RedisError as e:
            logger.error(f"❌ Failed to delete call data from Redis: {e}")
            return False
    
    def get_all_call_ids(self) -> list:
        """
        Get list of all active call IDs (for debugging)
        
        Returns:
            List of call_control_ids
        """
        if not self.client:
            return []
        
        try:
            keys = self.client.keys("call:*")
            return [key.replace("call:", "") for key in keys]
        except RedisError as e:
            logger.error(f"❌ Failed to retrieve call IDs: {e}")
            return []
    
    def is_connected(self) -> bool:
        """Check if Redis is connected and operational"""
        if not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except RedisError:
            return False
    
    def mark_session_ready(self, call_control_id: str, ttl: int = 3600) -> bool:
        """
        Mark that a call session is ready (for cross-worker coordination)
        
        Args:
            call_control_id: Unique call identifier
            ttl: Time-to-live in seconds
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            key = f"session_ready:{call_control_id}"
            self.client.setex(key, ttl, "1")
            logger.info(f"✅ Marked session ready in Redis: {call_control_id}")
            return True
        except RedisError as e:
            logger.error(f"❌ Failed to mark session ready: {e}")
            return False
    
    def is_session_ready(self, call_control_id: str) -> bool:
        """
        Check if a call session is ready (for cross-worker coordination)
        
        Args:
            call_control_id: Unique call identifier
        
        Returns:
            True if session is ready, False otherwise
        """
        if not self.client:
            return False
        
        try:
            key = f"session_ready:{call_control_id}"
            return bool(self.client.get(key))
        except RedisError:
            return False
    
    def set_flag(self, call_control_id: str, flag_name: str, value: str, expire: int = 10) -> bool:
        """
        Set a flag in Redis for cross-worker communication
        
        Args:
            call_control_id: Unique call identifier
            flag_name: Name of the flag
            value: Value to set
            expire: Expiration time in seconds
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            key = f"flag:{call_control_id}:{flag_name}"
            self.client.setex(key, expire, value)
            return True
        except RedisError as e:
            logger.error(f"❌ Failed to set flag {flag_name}: {e}")
            return False
    
    def get_flag(self, call_control_id: str, flag_name: str) -> Optional[str]:
        """
        Get a flag value from Redis
        
        Args:
            call_control_id: Unique call identifier
            flag_name: Name of the flag
        
        Returns:
            Flag value if exists, None otherwise
        """
        if not self.client:
            return None
        
        try:
            key = f"flag:{call_control_id}:{flag_name}"
            return self.client.get(key)
        except RedisError:
            return None
    
    def delete_flag(self, call_control_id: str, flag_name: str) -> bool:
        """
        Delete a flag from Redis
        
        Args:
            call_control_id: Unique call identifier
            flag_name: Name of the flag
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            key = f"flag:{call_control_id}:{flag_name}"
            self.client.delete(key)
            return True
        except RedisError:
            return False
    
    def add_playback_id(self, call_control_id: str, playback_id: str, ttl: int = 3600) -> bool:
        """
        Add a playback ID to the set of active playbacks for a call
        
        Args:
            call_control_id: Unique call identifier
            playback_id: Telnyx playback identifier
            ttl: Time-to-live in seconds
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            key = f"playbacks:{call_control_id}"
            self.client.sadd(key, playback_id)
            self.client.expire(key, ttl)
            logger.info(f"➕ Added playback {playback_id} to Redis for call {call_control_id}")
            return True
        except RedisError as e:
            logger.error(f"❌ Failed to add playback ID: {e}")
            return False
    
    def remove_playback_id(self, call_control_id: str, playback_id: str) -> int:
        """
        Remove a playback ID from the set of active playbacks
        
        Args:
            call_control_id: Unique call identifier
            playback_id: Telnyx playback identifier
        
        Returns:
            Number of remaining playback IDs, or -1 on error
        """
        if not self.client:
            return -1
        
        try:
            key = f"playbacks:{call_control_id}"
            self.client.srem(key, playback_id)
            remaining = self.client.scard(key)
            logger.info(f"➖ Removed playback {playback_id}, {remaining} remaining for call {call_control_id}")
            return remaining
        except RedisError as e:
            logger.error(f"❌ Failed to remove playback ID: {e}")
            return -1
    
    def get_playback_count(self, call_control_id: str) -> int:
        """
        Get count of active playback IDs for a call
        
        Args:
            call_control_id: Unique call identifier
        
        Returns:
            Number of active playbacks, or -1 on error
        """
        if not self.client:
            return -1
        
        try:
            key = f"playbacks:{call_control_id}"
            count = self.client.scard(key)
            return count
        except RedisError as e:
            logger.error(f"❌ Failed to get playback count: {e}")
            return -1
    
    def clear_playbacks(self, call_control_id: str) -> bool:
        """
        Clear all playback IDs for a call (used during interruptions)
        
        Args:
            call_control_id: Unique call identifier
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            key = f"playbacks:{call_control_id}"
            self.client.delete(key)
            logger.info(f"🧹 Cleared all playbacks for call {call_control_id}")
            return True
        except RedisError as e:
            logger.error(f"❌ Failed to clear playbacks: {e}")
            return False


# Global Redis service instance
redis_service = RedisService()
