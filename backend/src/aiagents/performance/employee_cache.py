"""
Employee-Specific Cache Operations

Extends the intelligent cache system for Employee CRUD operations:
- Employee search result caching
- Profile lookup caching
- Employee CRUD operation caching
- Cache invalidation strategies
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

from .intelligent_cache import IntelligentCache, CacheLevel, cache_manager
from .metrics_collector import metrics_collector, record_timer, increment_counter


class EmployeeCacheKeys:
    """Centralized cache key generation for employee operations"""
    
    @staticmethod
    def employee_by_id(employee_id: str) -> str:
        """Cache key for employee by ID"""
        return f"employee:id:{employee_id}"
    
    @staticmethod
    def employee_by_profile_id(profile_id: str) -> str:
        """Cache key for employee by profile ID"""
        return f"employee:profile:{profile_id}"
    
    @staticmethod
    def employee_by_number(employee_number: str) -> str:
        """Cache key for employee by employee number"""
        return f"employee:number:{employee_number}"
    
    @staticmethod
    def employee_search(query_hash: str) -> str:
        """Cache key for employee search results"""
        return f"employee:search:{query_hash}"
    
    @staticmethod
    def profile_by_name(name: str) -> str:
        """Cache key for profile search by name"""
        return f"profile:name:{hashlib.md5(name.lower().encode()).hexdigest()}"
    
    @staticmethod
    def profile_by_id(profile_id: str) -> str:
        """Cache key for profile by ID"""
        return f"profile:id:{profile_id}"
    
    @staticmethod
    def all_employees() -> str:
        """Cache key for all employees list"""
        return "employee:all"
    
    @staticmethod
    def employee_list_by_criteria(criteria_hash: str) -> str:
        """Cache key for filtered employee lists"""
        return f"employee:list:{criteria_hash}"


class EmployeeCacheManager:
    """
    Employee-specific cache manager with intelligent invalidation
    """
    
    def __init__(self):
        self.cache = cache_manager.get_cache("employee")
        self.default_ttl = 300  # 5 minutes
        self.search_ttl = 180   # 3 minutes for search results
        self.profile_ttl = 600  # 10 minutes for profiles
    
    async def cache_employee(self, employee_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache employee data with multiple keys for different access patterns"""
        try:
            start_time = datetime.now()
            
            employee_id = employee_data.get('employee_id')
            profile_id = employee_data.get('profile_id')
            employee_number = employee_data.get('employee_number')
            
            # If no employee_id, try to use profile_id as primary key
            if not employee_id and profile_id:
                # Use profile_id as the primary cache key
                primary_key = f"employee:profile:{profile_id}"
                await self.cache.set(
                    primary_key,
                    employee_data,
                    ttl or self.default_ttl,
                    CacheLevel.L1_MEMORY
                )
                
                # Cache with employee_number if available
                if employee_number:
                    await self.cache.set(
                        EmployeeCacheKeys.employee_by_number(employee_number),
                        employee_data,
                        ttl or self.default_ttl,
                        CacheLevel.L1_MEMORY
                    )
                
                duration = (datetime.now() - start_time).total_seconds()
                record_timer("employee_cache_set", duration)
                increment_counter("employee_cache_operations", 1)
                set_gauge("employee_cache_size_bytes", self.cache.stats.cache_size_bytes)
                
                return True
            elif not employee_id:
                print(f"Cannot cache employee data: missing both employee_id and profile_id")
                return False
            
            effective_ttl = ttl or self.default_ttl
            
            # Cache with primary key (employee_id)
            await self.cache.set(
                EmployeeCacheKeys.employee_by_id(employee_id),
                employee_data,
                effective_ttl,
                CacheLevel.L1_MEMORY
            )
            
            # Cache with secondary keys for different access patterns
            if profile_id:
                await self.cache.set(
                    EmployeeCacheKeys.employee_by_profile_id(profile_id),
                    employee_data,
                    effective_ttl,
                    CacheLevel.L1_MEMORY
                )
            
            if employee_number:
                await self.cache.set(
                    EmployeeCacheKeys.employee_by_number(employee_number),
                    employee_data,
                    effective_ttl,
                    CacheLevel.L1_MEMORY
                )
            
            # Record metrics
            duration = (datetime.now() - start_time).total_seconds()
            record_timer("employee_cache_set", duration)
            increment_counter("employee_cache_operations", 1)
            
            return True
            
        except Exception as e:
            print(f"Error caching employee: {e}")
            increment_counter("employee_cache_errors", 1)
            return False
    
    async def get_employee_by_id(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get employee from cache by ID"""
        try:
            start_time = datetime.now()
            
            result = await self.cache.get(EmployeeCacheKeys.employee_by_id(employee_id))
            
            duration = (datetime.now() - start_time).total_seconds()
            record_timer("employee_cache_get", duration)
            
            if result:
                increment_counter("employee_cache_hits", 1)
            else:
                increment_counter("employee_cache_misses", 1)
            
            return result
            
        except Exception as e:
            print(f"Error getting employee from cache: {e}")
            increment_counter("employee_cache_errors", 1)
            return None
    
    async def get_employee_by_profile_id(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get employee from cache by profile ID"""
        try:
            start_time = datetime.now()
            
            result = await self.cache.get(EmployeeCacheKeys.employee_by_profile_id(profile_id))
            
            duration = (datetime.now() - start_time).total_seconds()
            record_timer("employee_cache_get", duration)
            
            if result:
                increment_counter("employee_cache_hits", 1)
            else:
                increment_counter("employee_cache_misses", 1)
            
            return result
            
        except Exception as e:
            print(f"Error getting employee from cache: {e}")
            increment_counter("employee_cache_errors", 1)
            return None
    
    async def get_employee_by_number(self, employee_number: str) -> Optional[Dict[str, Any]]:
        """Get employee from cache by employee number"""
        try:
            start_time = datetime.now()
            
            result = await self.cache.get(EmployeeCacheKeys.employee_by_number(employee_number))
            
            duration = (datetime.now() - start_time).total_seconds()
            record_timer("employee_cache_get", duration)
            
            if result:
                increment_counter("employee_cache_hits", 1)
            else:
                increment_counter("employee_cache_misses", 1)
            
            return result
            
        except Exception as e:
            print(f"Error getting employee from cache: {e}")
            increment_counter("employee_cache_errors", 1)
            return None
    
    async def cache_employee_search(self, query_params: Dict[str, Any], results: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """Cache employee search results"""
        try:
            start_time = datetime.now()
            
            # Create a hash of the query parameters for the cache key
            query_str = json.dumps(query_params, sort_keys=True)
            query_hash = hashlib.md5(query_str.encode()).hexdigest()
            
            effective_ttl = ttl or self.search_ttl
            
            await self.cache.set(
                EmployeeCacheKeys.employee_search(query_hash),
                results,
                effective_ttl,
                CacheLevel.L1_MEMORY
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            record_timer("employee_search_cache_set", duration)
            increment_counter("employee_search_cache_operations", 1)
            
            return True
            
        except Exception as e:
            print(f"Error caching employee search: {e}")
            increment_counter("employee_cache_errors", 1)
            return False
    
    async def get_employee_search(self, query_params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Get employee search results from cache"""
        try:
            start_time = datetime.now()
            
            # Create the same hash as used for caching
            query_str = json.dumps(query_params, sort_keys=True)
            query_hash = hashlib.md5(query_str.encode()).hexdigest()
            
            result = await self.cache.get(EmployeeCacheKeys.employee_search(query_hash))
            
            duration = (datetime.now() - start_time).total_seconds()
            record_timer("employee_search_cache_get", duration)
            
            if result:
                increment_counter("employee_search_cache_hits", 1)
            else:
                increment_counter("employee_search_cache_misses", 1)
            
            return result
            
        except Exception as e:
            print(f"Error getting employee search from cache: {e}")
            increment_counter("employee_cache_errors", 1)
            return None
    
    async def cache_profile(self, profile_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache profile data"""
        try:
            start_time = datetime.now()
            
            profile_id = profile_data.get('profile_id') or profile_data.get('user_id')
            name = profile_data.get('first_name', '') + ' ' + profile_data.get('last_name', '')
            
            if not profile_id:
                return False
            
            effective_ttl = ttl or self.profile_ttl
            
            # Cache with profile ID
            await self.cache.set(
                EmployeeCacheKeys.profile_by_id(profile_id),
                profile_data,
                effective_ttl,
                CacheLevel.L1_MEMORY
            )
            
            # Cache with name if available
            if name.strip():
                await self.cache.set(
                    EmployeeCacheKeys.profile_by_name(name.strip()),
                    profile_data,
                    effective_ttl,
                    CacheLevel.L1_MEMORY
                )
            
            duration = (datetime.now() - start_time).total_seconds()
            record_timer("profile_cache_set", duration)
            increment_counter("profile_cache_operations", 1)
            
            return True
            
        except Exception as e:
            print(f"Error caching profile: {e}")
            increment_counter("employee_cache_errors", 1)
            return False
    
    async def get_profile_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get profile from cache by name"""
        try:
            start_time = datetime.now()
            
            result = await self.cache.get(EmployeeCacheKeys.profile_by_name(name.strip()))
            
            duration = (datetime.now() - start_time).total_seconds()
            record_timer("profile_cache_get", duration)
            
            if result:
                increment_counter("profile_cache_hits", 1)
            else:
                increment_counter("profile_cache_misses", 1)
            
            return result
            
        except Exception as e:
            print(f"Error getting profile from cache: {e}")
            increment_counter("employee_cache_errors", 1)
            return None
    
    async def invalidate_employee(self, employee_id: str, profile_id: Optional[str] = None, employee_number: Optional[str] = None) -> bool:
        """Invalidate employee cache entries"""
        try:
            keys_to_delete = [EmployeeCacheKeys.employee_by_id(employee_id)]
            
            if profile_id:
                keys_to_delete.append(EmployeeCacheKeys.employee_by_profile_id(profile_id))
            
            if employee_number:
                keys_to_delete.append(EmployeeCacheKeys.employee_by_number(employee_number))
            
            # Also invalidate search caches and lists
            keys_to_delete.extend([
                EmployeeCacheKeys.all_employees(),
                # Note: We could be more specific about which search caches to invalidate
                # but for simplicity, we'll let them expire naturally
            ])
            
            for key in keys_to_delete:
                await self.cache.delete(key)
            
            increment_counter("employee_cache_invalidations", 1)
            return True
            
        except Exception as e:
            print(f"Error invalidating employee cache: {e}")
            increment_counter("employee_cache_errors", 1)
            return False
    
    async def invalidate_all_employees(self) -> bool:
        """Invalidate all employee-related caches"""
        try:
            # This is a broad invalidation - in production, you might want to be more selective
            keys_to_delete = [
                EmployeeCacheKeys.all_employees(),
                # Add other broad cache keys as needed
            ]
            
            for key in keys_to_delete:
                await self.cache.delete(key)
            
            increment_counter("employee_cache_broad_invalidations", 1)
            return True
            
        except Exception as e:
            print(f"Error invalidating all employee caches: {e}")
            increment_counter("employee_cache_errors", 1)
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get employee cache statistics"""
        try:
            cache_stats = await self.cache.get_stats()
            
            return {
                "cache_hits": cache_stats.hits,
                "cache_misses": cache_stats.misses,
                "hit_rate": cache_stats.hit_rate,
                "cache_size_bytes": cache_stats.cache_size_bytes,
                "avg_response_time": cache_stats.avg_response_time,
                "evictions": cache_stats.evictions
            }
            
        except Exception as e:
            print(f"Error getting cache stats: {e}")
            return {}


# Global employee cache manager instance
employee_cache_manager = EmployeeCacheManager()


# Convenience functions for easy integration
async def cache_employee_data(employee_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
    """Cache employee data using the global manager"""
    return await employee_cache_manager.cache_employee(employee_data, ttl)


async def get_cached_employee_by_id(employee_id: str) -> Optional[Dict[str, Any]]:
    """Get cached employee by ID"""
    return await employee_cache_manager.get_employee_by_id(employee_id)


async def get_cached_employee_by_profile_id(profile_id: str) -> Optional[Dict[str, Any]]:
    """Get cached employee by profile ID"""
    return await employee_cache_manager.get_employee_by_profile_id(profile_id)


async def get_cached_employee_by_number(employee_number: str) -> Optional[Dict[str, Any]]:
    """Get cached employee by employee number"""
    return await employee_cache_manager.get_employee_by_number(employee_number)


async def cache_employee_search_results(query_params: Dict[str, Any], results: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
    """Cache employee search results"""
    return await employee_cache_manager.cache_employee_search(query_params, results, ttl)


async def get_cached_employee_search(query_params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Get cached employee search results"""
    return await employee_cache_manager.get_employee_search(query_params)


async def cache_profile_data(profile_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
    """Cache profile data"""
    return await employee_cache_manager.cache_profile(profile_data, ttl)


async def get_cached_profile_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get cached profile by name"""
    return await employee_cache_manager.get_profile_by_name(name)


async def invalidate_employee_cache(employee_id: str, profile_id: Optional[str] = None, employee_number: Optional[str] = None) -> bool:
    """Invalidate employee cache entries"""
    return await employee_cache_manager.invalidate_employee(employee_id, profile_id, employee_number)


async def invalidate_all_employee_caches() -> bool:
    """Invalidate all employee-related caches"""
    return await employee_cache_manager.invalidate_all_employees()


async def get_employee_cache_stats() -> Dict[str, Any]:
    """Get employee cache statistics"""
    return await employee_cache_manager.get_cache_stats()
