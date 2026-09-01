from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.core.enums import Role


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    date_naissance: Optional[date] = None
    telephone: Optional[str] = None
    sexe: Optional[str] = None  # 'M', 'F', 'Autre'
    pays_residence: Optional[str] = None
    is_active: bool = True
    role: Role = Role.USER
    hospital_id: Optional[int] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    date_naissance: Optional[date] = None
    telephone: Optional[str] = None
    sexe: Optional[str] = None
    pays_residence: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[Role] = None
    password: Optional[str] = None
    role_id: Optional[int] = None
    hospital_id: Optional[int] = None


class UserResponse(UserBase):
    id: int
    is_superuser: bool
    role_id: Optional[int] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
