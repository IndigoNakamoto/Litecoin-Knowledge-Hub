from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId # Added for json_encoders

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserInDBBase(UserBase):
    id: str = Field(..., alias="_id")
    hashed_password: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Renamed from orm_mode in Pydantic V2
        validate_by_name = True # Renamed from allow_population_by_field_name in Pydantic V2
        json_encoders = {ObjectId: str} # Ensure ObjectId is handled for JSON serialization
        arbitrary_types_allowed = True # Allow custom types like ObjectId

class User(UserInDBBase):
    pass

class UserInDB(UserInDBBase):
    pass

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
