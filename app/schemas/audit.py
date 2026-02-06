from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    method: str
    path: str
    query_params: Optional[str] = None
    user_id: Optional[int] = None
    user_role: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    status_code: int
    request_body: Optional[str] = None
    response_body: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
