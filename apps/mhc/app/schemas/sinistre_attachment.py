from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SinistreAttachmentInfo(BaseModel):
    id: int
    attachment_type: str
    file_name: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by_id: Optional[int] = None
    uploaded_by_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
