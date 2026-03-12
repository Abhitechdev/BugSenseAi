"""Authentication and authorization middleware for admin endpoints."""

import structlog
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = structlog.get_logger(__name__)

class AdminAuthMiddleware:
    """Middleware to protect admin-only endpoints."""
    
    def __init__(self, admin_token: str):
        self.admin_token = admin_token
        self.security = HTTPBearer(auto_error=False)
    
    async def __call__(self, request: Request):
        # Skip auth for non-destructive endpoints
        if request.url.path not in ["/api/history/all", "/api/history/category/{category}", "/api/history/{analysis_id}"]:
            return
        
        # Extract token from header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("admin_auth_missing", path=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            # Parse Bearer token
            if not auth_header.startswith("Bearer "):
                raise ValueError("Invalid authorization header format")
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            if token != self.admin_token:
                logger.warning("admin_auth_invalid", path=request.url.path)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid admin token",
                )
                
        except (ValueError, IndexError) as e:
            logger.warning("admin_auth_parse_error", error=str(e), path=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info("admin_auth_success", path=request.url.path)
        return


class AdminAuthRequired:
    """Dependency to require admin authentication."""
    
    def __init__(self, admin_token: str):
        self.admin_token = admin_token
    
    async def __call__(self, request: Request):
        middleware = AdminAuthMiddleware(self.admin_token)
        return await middleware(request)