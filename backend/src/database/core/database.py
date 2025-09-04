import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from pathlib import Path

# Get the directory where this file is located
current_dir = Path(__file__).parent
# Go up to the backend directory and load .env from there
# From src/database/core/ we need to go up 3 levels to reach backend/
backend_dir = current_dir.parent.parent.parent
env_file_path = backend_dir / ".env"
load_dotenv(env_file_path)

DATABASE_URL = os.getenv("DATABASE_URL")

# 🚀 PHASE 1 OPTIMIZATION: Enhanced database connection pool for better performance
# TODO: If connection issues occur, revert to basic engine configuration
engine = create_engine(
    DATABASE_URL, 
    pool_recycle=3600,           # Keep existing recycle time
    pool_size=10,                # 🚀 OPTIMIZATION: Set minimum pool size to 10 connections
    max_overflow=20,             # 🚀 OPTIMIZATION: Allow up to 20 additional connections (total 30)
    pool_pre_ping=True,          # 🚀 OPTIMIZATION: Validate connections before use
    pool_timeout=30,             # 🚀 OPTIMIZATION: 30s timeout for getting connection from pool
    connect_args={
        "connect_timeout": 10,   # 🚀 OPTIMIZATION: 10s timeout for initial connection
        "application_name": "ConsultEase_Backend"  # 🚀 OPTIMIZATION: Better connection tracking
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()