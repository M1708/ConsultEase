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

engine = create_engine(DATABASE_URL, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()