import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from bson import ObjectId
import datetime

from . import models
from ..auth.security import get_password_hash

# Retrieve MongoDB URI from environment variables
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set.")

client = AsyncIOMotorClient(MONGO_URI)
database = client.litecoin_rag_chat
users_collection = database.get_collection("cms_users")

async def get_user_by_email(email: str) -> Optional[models.User]:
    user = await users_collection.find_one({"email": email})
    if user:
        user["_id"] = str(user["_id"]) # Convert ObjectId to string
        return models.User.model_validate(user)
    return None

async def create_user(user_data: models.UserCreate) -> models.User:
    user_dict = user_data.model_dump() # Use model_dump for Pydantic V2
    user_dict["hashed_password"] = get_password_hash(user_data.password)
    del user_dict["password"]
    
    user_dict["created_at"] = datetime.datetime.utcnow()
    user_dict["updated_at"] = datetime.datetime.utcnow()
    
    result = await users_collection.insert_one(user_dict)
    new_user = await users_collection.find_one({"_id": result.inserted_id})
    new_user["_id"] = str(new_user["_id"]) # Convert ObjectId to string
    return models.User.model_validate(new_user)
