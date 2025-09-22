"""
File Cache Service for optimizing file uploads in agent workflows.

This service stores file data temporarily and provides references that can be passed
through the agent workflow instead of the actual file data, significantly reducing
memory usage and processing time.
"""

import uuid
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import threading


class FileCacheService:
    """Service for caching file data with automatic cleanup."""
    
    def __init__(self, default_ttl_minutes: int = 30):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl_minutes * 60  # Convert to seconds
        self._lock = threading.Lock()
    
    def store_file(self, file_data: str, filename: str, file_size: int, mime_type: str) -> str:
        """
        Store file data and return a reference ID.
        
        Args:
            file_data: Base64 encoded file content
            filename: Original filename
            file_size: File size in bytes
            mime_type: MIME type of the file
            
        Returns:
            str: Reference ID that can be used to retrieve the file
        """
        with self._lock:
            # Generate unique reference ID
            ref_id = str(uuid.uuid4())
            
            # Store file data with metadata
            self._cache[ref_id] = {
                'file_data': file_data,
                'filename': filename,
                'file_size': file_size,
                'mime_type': mime_type,
                'created_at': time.time(),
                'expires_at': time.time() + self._default_ttl
            }
            
            print(f"🔍 DEBUG: File cached with ref_id: {ref_id}, size: {file_size} bytes")
            return ref_id
    
    def get_file(self, ref_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve file data by reference ID.
        
        Args:
            ref_id: Reference ID returned by store_file
            
        Returns:
            Dict containing file data and metadata, or None if not found/expired
        """
        with self._lock:
            if ref_id not in self._cache:
                print(f"🔍 DEBUG: File ref_id {ref_id} not found in cache")
                return None
            
            file_info = self._cache[ref_id]
            
            # Check if expired
            if time.time() > file_info['expires_at']:
                del self._cache[ref_id]
                print(f"🔍 DEBUG: File ref_id {ref_id} expired and removed")
                return None
            
            print(f"🔍 DEBUG: File retrieved from cache: {ref_id}, size: {file_info['file_size']} bytes")
            return file_info
    
    def remove_file(self, ref_id: str) -> bool:
        """
        Remove file from cache.
        
        Args:
            ref_id: Reference ID to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        with self._lock:
            if ref_id in self._cache:
                del self._cache[ref_id]
                print(f"🔍 DEBUG: File ref_id {ref_id} removed from cache")
                return True
            return False
    
    def cleanup_expired(self) -> int:
        """
        Remove expired files from cache.
        
        Returns:
            int: Number of files removed
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                ref_id for ref_id, file_info in self._cache.items()
                if current_time > file_info['expires_at']
            ]
            
            for ref_id in expired_keys:
                del self._cache[ref_id]
            
            if expired_keys:
                print(f"🔍 DEBUG: Cleaned up {len(expired_keys)} expired files")
            
            return len(expired_keys)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            current_time = time.time()
            active_files = len(self._cache)
            expired_files = sum(
                1 for file_info in self._cache.values()
                if current_time > file_info['expires_at']
            )
            
            total_size = sum(
                file_info['file_size'] for file_info in self._cache.values()
                if current_time <= file_info['expires_at']
            )
            
            return {
                'active_files': active_files,
                'expired_files': expired_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }


# Global instance
file_cache = FileCacheService(default_ttl_minutes=30)

# Start cleanup thread

def cleanup_worker():
    """Background thread to clean up expired files."""
    while True:
        try:
            time.sleep(300)  # Run every 5 minutes
            expired_count = file_cache.cleanup_expired()
            if expired_count > 0:
                print(f"🔍 DEBUG: Cleaned up {expired_count} expired files from cache")
        except Exception as e:
            print(f"🔍 DEBUG: Error in cleanup worker: {e}")

# Start cleanup thread in daemon mode
cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
cleanup_thread.start()
