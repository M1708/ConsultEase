from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.database.core.database import get_db, async_engine, Base
from src.database.api import clients, contracts, client_contacts, deliverables, time_entries, expenses, employees, chat, chat_sessions
from src.auth import routes as auth_routes
from src.auth.middleware import auth_middleware
from  src.auth.session_manager import SessionManager

# Import performance systems
from src.aiagents.performance.intelligent_cache import cache_manager
from src.aiagents.performance.optimization_engine import start_optimization_engine, stop_optimization_engine
from src.aiagents.performance.metrics_collector import metrics_collector


# Create database tables
#Base.metadata.create_all(bind=engine)

# Create tables asynchronously - DISABLED for pgbouncer compatibility
async def create_tables():
    # Skip table creation to avoid pgbouncer prepared statements error
    # Tables should already exist in the database
    pass


app = FastAPI(
    title="ConsultEase API",
    version="1.0.0",
    description="AI-powered Client and Contract Management API with Authentication"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://effiscale.vercel.app", "http://localhost:3001"],  # React dev server (both ports)
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
    """Initialize systems on startup"""
    # Initialize database tables
    await create_tables()
    print("✅ Database tables created successfully")
    
    # Initialize performance systems
    try:
        # Start optimization engine
        await start_optimization_engine()
        print("✅ Performance optimization engine started")
        
        # Initialize cache manager
        cache_manager.get_cache("employee")  # Initialize employee cache
        print("✅ Intelligent cache system initialized")
        
        # Set up performance monitoring
        metrics_collector.set_alert_threshold("employee_cache_hit_rate", low_threshold=0.7)
        metrics_collector.set_alert_threshold("employee_operation_duration", high_threshold=5.0)
        print("✅ Performance monitoring configured")
        
    except Exception as e:
        print(f"⚠️ Warning: Performance systems initialization failed: {e}")
        print("Application will continue without performance optimizations")

@app.on_event("shutdown")
async def shutdown():
    """Clean shutdown"""
    try:
        # Stop optimization engine
        await stop_optimization_engine()
        print("✅ Performance optimization engine stopped")
    except Exception as e:
        print(f"⚠️ Warning: Error stopping optimization engine: {e}")
    
    # Dispose database engine
    await async_engine.dispose()
    print("✅ Database engine disposed")

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
        
        # Get performance metrics
        performance_stats = metrics_collector.get_all_metrics_summary()
        
        return {
            "status": "healthy", 
            "database": "connected",
            "redis": "connected",
            "performance": {
                "total_metrics": performance_stats.get("total_metrics", 0),
                "collection_overhead_ms": performance_stats.get("collection_overhead", {}).get("avg_ms", 0),
                "cache_stats": performance_stats.get("gauges", {})
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "database": "disconnected", 
            "redis": "disconnected",
            "error": str(e)
        }

@app.get("/performance")
async def performance_metrics():
    """Performance metrics endpoint"""
    try:
        # Get comprehensive performance metrics
        metrics_summary = metrics_collector.get_all_metrics_summary()
        
        # Get cache statistics
        from src.aiagents.performance.employee_cache import get_employee_cache_stats
        cache_stats = await get_employee_cache_stats()
        
        return {
            "metrics": metrics_summary,
            "cache": cache_stats,
            "timestamp": metrics_summary.get("collection_time")
        }
    except Exception as e:
        return {
            "error": f"Failed to get performance metrics: {str(e)}"
        }
