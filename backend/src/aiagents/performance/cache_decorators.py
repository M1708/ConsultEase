"""
Cache Decorators for Employee CRUD Operations

Provides decorators for automatic caching of Employee operations:
- @cache_employee_result - Cache employee data after successful operations
- @cache_search_results - Cache search results
- @invalidate_cache_on_update - Invalidate cache on updates
- @cache_profile_lookup - Cache profile lookups
"""

import asyncio
import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime

from .employee_cache import (
    employee_cache_manager,
    cache_employee_data,
    cache_employee_search_results,
    cache_profile_data,
    invalidate_employee_cache,
    get_cached_employee_by_id,
    get_cached_employee_by_profile_id,
    get_cached_employee_by_number,
    get_cached_employee_search,
    get_cached_profile_by_name
)
from .metrics_collector import record_timer, increment_counter


def cache_employee_result(
    cache_ttl: Optional[int] = None,
    cache_key_param: str = "employee_id",
    result_key: str = "data"
):
    """
    Decorator to cache employee data after successful operations.
    
    Args:
        cache_ttl: Time to live for cache entry (seconds)
        cache_key_param: Parameter name to use as cache key
        result_key: Key in result dict containing employee data
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            try:
                # Execute the original function
                result = await func(*args, **kwargs)
                
                # Check if operation was successful
                if (hasattr(result, 'success') and result.success) or \
                   (isinstance(result, dict) and result.get('success', False)):
                    
                    # Extract employee data for caching
                    employee_data = None
                    if hasattr(result, result_key):
                        employee_data = getattr(result, result_key)
                    elif isinstance(result, dict) and result_key in result:
                        employee_data = result[result_key]
                    
                    # Handle EmployeeToolResult objects specifically
                    if hasattr(result, 'data') and result.data:
                        employee_data = result.data
                    
                    if employee_data and isinstance(employee_data, dict):
                        # Check if employee_id is available, if not use profile_id as fallback
                        employee_id = employee_data.get('employee_id')
                        profile_id = employee_data.get('profile_id')
                        
                        # Only cache if we have either employee_id or profile_id
                        if employee_id or profile_id:
                            try:
                                await cache_employee_data(employee_data, cache_ttl)
                                duration = (datetime.now() - start_time).total_seconds()
                                record_timer("cache_employee_result_decorator", duration)
                                increment_counter("employee_result_cached", 1)
                            except Exception as cache_error:
                                # Log cache error but don't fail the operation
                                print(f"Cache error (non-blocking): {cache_error}")
                                increment_counter("employee_result_cache_errors", 1)
                        else:
                            # Log when we can't cache due to missing keys
                            print(f"Cannot cache employee data: missing employee_id and profile_id")
                            increment_counter("employee_result_cache_skipped", 1)
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                record_timer("cache_employee_result_decorator_error", duration)
                increment_counter("employee_result_cache_errors", 1)
                print(f"Error in cache_employee_result decorator: {e}")
                return await func(*args, **kwargs)  # Return original result on error
        
        return wrapper
    return decorator


def cache_search_results(
    cache_ttl: Optional[int] = None,
    query_params_func: Optional[Callable] = None
):
    """
    Decorator to cache search results.
    
    Args:
        cache_ttl: Time to live for cache entry (seconds)
        query_params_func: Function to extract query parameters from args/kwargs
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            try:
                # Extract query parameters for cache key
                query_params = {}
                if query_params_func:
                    query_params = query_params_func(*args, **kwargs)
                else:
                    # Default: use kwargs as query parameters
                    query_params = {k: v for k, v in kwargs.items() if v is not None}
                
                # Try to get from cache first
                cached_results = await get_cached_employee_search(query_params)
                if cached_results is not None:
                    duration = (datetime.now() - start_time).total_seconds()
                    record_timer("cache_search_results_hit", duration)
                    increment_counter("search_cache_hits", 1)
                    
                    # Return cached results in the same format as the original function
                    # For EmployeeToolResult, we need to reconstruct the proper format
                    if hasattr(func, '__annotations__') and 'return' in func.__annotations__:
                        # Check if the function returns EmployeeToolResult
                        return_type = func.__annotations__['return']
                        if 'EmployeeToolResult' in str(return_type):
                            # Reconstruct EmployeeToolResult from cached data
                            from src.aiagents.tools.employee_tools import EmployeeToolResult
                            result = EmployeeToolResult(
                                success=True,
                                message=f"📋 Found {cached_results.get('count', 0)} employees (cached results)",
                                data=cached_results
                            )
                            return result
                        else:
                            return cached_results
                    return cached_results
                
                # Cache miss - execute original function
                result = await func(*args, **kwargs)
                
                # Check if operation was successful and cache the results
                if (hasattr(result, 'success') and result.success) or \
                   (isinstance(result, dict) and result.get('success', False)):
                    
                    # Extract search results for caching
                    search_data = None
                    if hasattr(result, 'data'):
                        search_data = result.data
                    elif isinstance(result, dict) and 'data' in result:
                        search_data = result['data']
                    
                    if search_data and isinstance(search_data, dict):
                        try:
                            # Cache the search results
                            await cache_employee_search_results(query_params, search_data, cache_ttl)
                            
                            duration = (datetime.now() - start_time).total_seconds()
                            record_timer("cache_search_results_miss", duration)
                            increment_counter("search_cache_misses", 1)
                        except Exception as cache_error:
                            print(f"Cache error (non-blocking): {cache_error}")
                            increment_counter("search_cache_errors", 1)
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                record_timer("cache_search_results_error", duration)
                increment_counter("search_cache_errors", 1)
                print(f"Error in cache_search_results decorator: {e}")
                return await func(*args, **kwargs)  # Return original result on error
        
        return wrapper
    return decorator


def invalidate_cache_on_update(
    employee_id_param: str = "employee_id",
    profile_id_param: Optional[str] = None,
    employee_number_param: Optional[str] = None
):
    """
    Decorator to invalidate cache entries after successful updates.
    
    Args:
        employee_id_param: Parameter name containing employee_id
        profile_id_param: Parameter name containing profile_id
        employee_number_param: Parameter name containing employee_number
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            try:
                # Execute the original function
                result = await func(*args, **kwargs)
                
                # Check if operation was successful
                if (hasattr(result, 'success') and result.success) or \
                   (isinstance(result, dict) and result.get('success', False)):
                    
                    # Extract parameters for cache invalidation
                    employee_id = kwargs.get(employee_id_param)
                    profile_id = kwargs.get(profile_id_param) if profile_id_param else None
                    employee_number = kwargs.get(employee_number_param) if employee_number_param else None
                    
                    # For create operations, try to get employee_id from result data
                    if not employee_id and hasattr(result, 'data') and result.data:
                        employee_id = result.data.get('employee_id')
                    
                    if employee_id:
                        # Invalidate cache entries
                        await invalidate_employee_cache(employee_id, profile_id, employee_number)
                        
                        duration = (datetime.now() - start_time).total_seconds()
                        record_timer("invalidate_cache_on_update", duration)
                        increment_counter("cache_invalidations", 1)
                    else:
                        # Log when we can't invalidate due to missing employee_id
                        print(f"Cannot invalidate cache: missing employee_id for {func.__name__}")
                        increment_counter("cache_invalidation_skipped", 1)
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                record_timer("invalidate_cache_on_update_error", duration)
                increment_counter("cache_invalidation_errors", 1)
                print(f"Error in invalidate_cache_on_update decorator: {e}")
                return await func(*args, **kwargs)  # Return original result on error
        
        return wrapper
    return decorator


def cache_profile_lookup(cache_ttl: Optional[int] = None):
    """
    Decorator to cache profile lookups.
    
    Args:
        cache_ttl: Time to live for cache entry (seconds)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            try:
                # Extract search name for cache key
                search_name = args[0] if args else kwargs.get('search_name', '')
                
                # Try to get from cache first
                cached_profile = await get_cached_profile_by_name(search_name)
                if cached_profile is not None:
                    duration = (datetime.now() - start_time).total_seconds()
                    record_timer("cache_profile_lookup_hit", duration)
                    increment_counter("profile_cache_hits", 1)
                    return cached_profile
                
                # Cache miss - execute original function
                result = await func(*args, **kwargs)
                
                # Check if operation was successful and cache the results
                if (hasattr(result, 'success') and result.success) or \
                   (isinstance(result, dict) and result.get('success', False)):
                    
                    # Extract profile data for caching
                    profile_data = None
                    if hasattr(result, 'data'):
                        profile_data = result.data
                    elif isinstance(result, dict) and 'data' in result:
                        profile_data = result['data']
                    
                    if profile_data and isinstance(profile_data, dict):
                        try:
                            # Cache the profile data
                            await cache_profile_data(profile_data, cache_ttl)
                            
                            duration = (datetime.now() - start_time).total_seconds()
                            record_timer("cache_profile_lookup_miss", duration)
                            increment_counter("profile_cache_misses", 1)
                        except Exception as cache_error:
                            print(f"Cache error (non-blocking): {cache_error}")
                            increment_counter("profile_cache_errors", 1)
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                record_timer("cache_profile_lookup_error", duration)
                increment_counter("profile_cache_errors", 1)
                print(f"Error in cache_profile_lookup decorator: {e}")
                return await func(*args, **kwargs)  # Return original result on error
        
        return wrapper
    return decorator


def cache_employee_lookup(cache_ttl: Optional[int] = None):
    """
    Decorator to cache employee lookup operations.
    
    Args:
        cache_ttl: Time to live for cache entry (seconds)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            try:
                # Extract lookup parameters for cache key
                employee_id = kwargs.get('employee_id')
                profile_id = kwargs.get('profile_id')
                employee_number = kwargs.get('employee_number')
                
                # Try to get from cache first
                cached_employee = None
                if employee_id:
                    cached_employee = await get_cached_employee_by_id(str(employee_id))
                elif profile_id:
                    cached_employee = await get_cached_employee_by_profile_id(profile_id)
                elif employee_number:
                    cached_employee = await get_cached_employee_by_number(employee_number)
                
                if cached_employee is not None:
                    duration = (datetime.now() - start_time).total_seconds()
                    record_timer("cache_employee_lookup_hit", duration)
                    increment_counter("employee_lookup_cache_hits", 1)
                    return cached_employee
                
                # Cache miss - execute original function
                result = await func(*args, **kwargs)
                
                # Check if operation was successful and cache the results
                if (hasattr(result, 'success') and result.success) or \
                   (isinstance(result, dict) and result.get('success', False)):
                    
                    # Extract employee data for caching
                    employee_data = None
                    if hasattr(result, 'data'):
                        employee_data = result.data
                    elif isinstance(result, dict) and 'data' in result:
                        employee_data = result['data']
                    
                    if employee_data and isinstance(employee_data, dict):
                        try:
                            # Cache the employee data
                            await cache_employee_data(employee_data, cache_ttl)
                            
                            duration = (datetime.now() - start_time).total_seconds()
                            record_timer("cache_employee_lookup_miss", duration)
                            increment_counter("employee_lookup_cache_misses", 1)
                        except Exception as cache_error:
                            print(f"Cache error (non-blocking): {cache_error}")
                            increment_counter("employee_lookup_cache_errors", 1)
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                record_timer("cache_employee_lookup_error", duration)
                increment_counter("employee_lookup_cache_errors", 1)
                print(f"Error in cache_employee_lookup decorator: {e}")
                return await func(*args, **kwargs)  # Return original result on error
        
        return wrapper
    return decorator


def performance_tracked(operation_name: str):
    """
    Decorator to track performance metrics for operations.
    
    Args:
        operation_name: Name of the operation for metrics tracking
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            try:
                result = await func(*args, **kwargs)
                
                duration = (datetime.now() - start_time).total_seconds()
                record_timer(f"{operation_name}_duration", duration)
                increment_counter(f"{operation_name}_success", 1)
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                record_timer(f"{operation_name}_error", duration)
                increment_counter(f"{operation_name}_errors", 1)
                raise e
        
        return wrapper
    return decorator


# Convenience decorator combinations
def cached_employee_operation(
    cache_ttl: Optional[int] = None,
    invalidate_on_update: bool = True,
    track_performance: bool = True
):
    """
    Combined decorator for employee operations with caching and invalidation.
    
    Args:
        cache_ttl: Time to live for cache entry (seconds)
        invalidate_on_update: Whether to invalidate cache on updates
        track_performance: Whether to track performance metrics
    """
    def decorator(func: Callable) -> Callable:
        # Only apply performance tracking for CREATE operations to avoid overhead
        if track_performance and 'create' in func.__name__.lower():
            func = performance_tracked(func.__name__)(func)
        elif track_performance and 'create' not in func.__name__.lower():
            # Apply full caching for non-CREATE operations
            func = performance_tracked(func.__name__)(func)
            func = cache_employee_result(cache_ttl=cache_ttl)(func)
        
        # Only apply cache invalidation for UPDATE operations, not CREATE
        if invalidate_on_update and 'update' in func.__name__.lower():
            func = invalidate_cache_on_update()(func)
        
        return func
    
    return decorator


def cached_search_operation(
    cache_ttl: Optional[int] = None,
    track_performance: bool = True
):
    """
    Combined decorator for search operations with caching.
    
    Args:
        cache_ttl: Time to live for cache entry (seconds)
        track_performance: Whether to track performance metrics
    """
    def decorator(func: Callable) -> Callable:
        # Apply performance tracking if requested
        if track_performance:
            func = performance_tracked(func.__name__)(func)
        
        # Apply caching for search results
        func = cache_search_results(cache_ttl=cache_ttl)(func)
        
        return func
    
    return decorator
