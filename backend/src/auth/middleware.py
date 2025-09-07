from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import jwt
from supabase import create_client
import os

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)

async def auth_middleware(request: Request, call_next):
    """Global authentication middleware"""
    
    if request.method == "OPTIONS":
        response = await call_next(request)
        return response

    # Skip auth for certain paths
    skip_auth_paths = [
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/api/auth/profile/",  # This specific endpoint bypasses normal auth
        "/api/chat/greeting",  # Fast greeting endpoint without auth
        "/api/chat/message",   # TEMPORARY: Skip auth for testing employee creation
    ]
    
    if any(request.url.path.startswith(path) for path in skip_auth_paths):
        response = await call_next(request)
        return response
    
    # Check for Authorization header
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing or invalid authorization header"}
        )
    
    try:
        token = auth_header.split(" ")[1]
        
        # Verify token with Supabase
        response = supabase.auth.get_user(token)
        if not response.user:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token"}
            )
        
        # Add user info to request state
        request.state.auth_user = response.user
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": f"Authentication failed: {str(e)}"}
        )
    
    response = await call_next(request)
    return response