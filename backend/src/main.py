from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.database.core.database import get_db, async_engine, Base
from src.database.api import clients, contracts, client_contacts, deliverables, time_entries, expenses, employees, chat, chat_sessions
from src.auth import routes as auth_routes
from src.auth.middleware import auth_middleware
from  src.auth.session_manager import SessionManager


# Create database tables
#Base.metadata.create_all(bind=engine)

# Create tables asynchronously - DISABLED for pgbouncer compatibility
async def create_tables():
    # Skip table creation to avoid pgbouncer prepared statements error
    # Tables should already exist in the database
    print("🔧 DEBUG: Skipping table creation for pgbouncer compatibility")
    pass


app = FastAPI(
    title="ConsultEase API",
    version="1.0.0",
    description="AI-powered Client and Contract Management API with Authentication"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev server (both ports)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Add authentication middleware
app.middleware("http")(auth_middleware)


# Include routers
app.include_router(auth_routes.router, prefix="/api/auth", tags=["authentication"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(contracts.router, prefix="/api/contracts", tags=["contracts"])
app.include_router(client_contacts.router, prefix="/api/client-contacts", tags=["client-contacts"])
app.include_router(deliverables.router, prefix="/api/deliverables", tags=["deliverables"])
app.include_router(time_entries.router, prefix="/api/time-entries", tags=["time-entries"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["expenses"])
app.include_router(employees.router, prefix="/api/employees", tags=["employees"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(chat_sessions.router, prefix="/api/chat", tags=["chat-sessions"])

@app.on_event("startup")
async def startup():
    """Initialize database tables on startup"""
    await create_tables()
    print("Database tables created successfully")

@app.on_event("shutdown")
async def shutdown():
    """Clean shutdown"""
    await async_engine.dispose()

@app.get("/")
def root():
    return {"message": "ConsultEase API is running with authentication!"}

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        await db.execute(text('SELECT 1'))
        
        # Test Redis connection
        session_manager = SessionManager()
        session_manager.redis_client.ping()
        
        return {
            "status": "healthy", 
            "database": "connected",
            "redis": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "database": "disconnected", 
            "redis": "disconnected",
            "error": str(e)
        }
