import os
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
from contextlib import asynccontextmanager
from sqlalchemy.pool import NullPool

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
from pathlib import Path

# Setup logging for performance monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment setup (keep your existing logic)
current_dir = Path(__file__).parent
backend_dir = current_dir.parent.parent.parent
env_file_path = backend_dir / ".env"
load_dotenv(env_file_path)

DATABASE_URL = os.getenv("DATABASE_URL")

# PGBOUNCER DETECTION: Check if using connection pooler
IS_PGBOUNCER = "pooler.supabase.com" in (DATABASE_URL or "") or "pooler" in (DATABASE_URL or "").lower()

# Convert PostgreSQL URL to async format
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Keep using pooler URL but with enhanced pgbouncer compatibility

# FORCE PGBOUNCER COMPATIBILITY: Always use pgbouncer settings for Supabase
if IS_PGBOUNCER or "supabase.com" in (DATABASE_URL or ""):
    IS_PGBOUNCER = True

# CRITICAL: Force pgbouncer compatibility for ALL Supabase connections
if DATABASE_URL and ("supabase.com" in DATABASE_URL or "pooler" in DATABASE_URL.lower()):
    IS_PGBOUNCER = True

# 🚀 ASYNC ENGINE: OPTIMIZED FOR PERFORMANCE - Balanced approach
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    # Use QueuePool for better performance with connection reuse
    poolclass=None,  # Use default QueuePool for better performance
    
    # ASYNC CONNECTION SETTINGS - Performance optimized
    connect_args={
        # PGBOUNCER COMPATIBILITY: Disable prepared statements (CRITICAL for Supabase pooler)
        "statement_cache_size": 0,                    # Disable statement caching
        "prepared_statement_cache_size": 0,           # Disable prepared statement caching
        
        # CONNECTION TIMEOUTS - Optimized for AI queries
        "timeout": 5,                                 # 5s connection timeout (faster)
        "command_timeout": 15,                        # 15s query timeout (faster)
        
        # SERVER SETTINGS - Performance optimized
        "server_settings": {
            "application_name": "AgenticAI_Async",
            "jit": "off",                             # Disable JIT for simple AI queries
            "work_mem": "4MB",                        # Optimize for small, fast queries
            "statement_timeout": "15s",               # Hard limit on query execution
        },
    },
    
    # PERFORMANCE SETTINGS
    echo=False,                      # Disable SQL logging in production
    future=True,                     # SQLAlchemy 2.0 style
    
    # CONNECTION POOL SETTINGS - Optimized for performance
    pool_size=5,                     # Small pool size for efficiency
    max_overflow=10,                 # Allow overflow for bursts
    pool_pre_ping=True,              # Enable pre-ping for connection health
    pool_recycle=3600,              # Recycle connections every hour
    pool_timeout=10,                # 10s timeout for getting connection from pool
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Keep objects accessible after commit
    autocommit=False,
    autoflush=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session  # This is what Depends() needs
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()

@asynccontextmanager
async def get_ai_db():
    async with AsyncSessionLocal() as session:  # ← Uses the factory
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise

async def test_async_connection():
    """Test async database connection for pgbouncer compatibility"""
    try:
        async with get_ai_db() as session:
            # Simple test query that doesn't use prepared statements
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            return True
    except Exception as e:
        return False

Base = declarative_base()