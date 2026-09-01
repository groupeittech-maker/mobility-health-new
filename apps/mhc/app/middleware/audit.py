import json
from datetime import datetime
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.audit import AuditLog
from app.core.security import decode_token

# Create a simple in-memory store for audit logs
# In production, you might want to use a separate database or service
audit_logs = []


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for auditing API requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Get user info from token if available
        user_id = None
        user_role = None
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            if payload:
                user_id = payload.get("sub")
                user_role = payload.get("role")
        
        # Prepare audit data
        audit_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": str(request.url.path),
            "query_params": str(request.query_params),
            "user_id": user_id,
            "user_role": user_role,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
        
        # Process request
        response = await call_next(request)
        
        # Add response info
        audit_data["status_code"] = response.status_code
        
        # Store audit log (in production, save to database)
        audit_logs.append(audit_data)
        
        # In production, you would save to database:
        # db = SessionLocal()
        # try:
        #     audit_log = AuditLog(**audit_data)
        #     db.add(audit_log)
        #     db.commit()
        # finally:
        #     db.close()
        
        return response


















