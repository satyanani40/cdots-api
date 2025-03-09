import uuid

from fastapi import APIRouter, HTTPException, Depends, Form, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
import jwt
import os
from pydantic import BaseModel, EmailStr, Field


from cdots.core.config import SECRET_KEY, ALGORITHM, pwd_context
from cdots.db.mongo.mongo_connection import MongoDBConnection
from cdots.core.config import MONGO_URI, MONGO_DB_NAME
from cdots.core.config import STATIC_FOLDER_PATH


router = APIRouter(prefix="/api/v1", tags=["User Authentication"])

# Initialize MongoDB connection
db_connection = MongoDBConnection(uri=MONGO_URI, db_name=MONGO_DB_NAME)
db = db_connection.get_db()

# Define upload folder
profile_pics = "profile_pics"
abs_profile_pics_path = os.path.join(STATIC_FOLDER_PATH,profile_pics)
os.makedirs(abs_profile_pics_path, exist_ok=True)


class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=1, description="Full name cannot be empty")
    email: EmailStr = Field(..., description="Valid email required")
    password: str = Field(..., min_length=6, description="Password is mandatory and must be at least 6 characters long")
    re_enter_password: str = Field(..., min_length=6, description="Passwords must match", alias="re_enter_password", widget="password")
    profile_pic: UploadFile = File(None)


@router.post("/register/")
async def register_user(
        full_name: str = Form(...),
        email: EmailStr = Form(...),
        password: str = Form(..., min_length=6),
        re_enter_password: str = Form(..., min_length=6, alias="re_enter_password", widget="password"),
        profile_pic: UploadFile = File(None)
):
    if password != re_enter_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    existing_user = db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = pwd_context.hash(password)

    profile_pic_path = None
    if profile_pic:
        pic_full_name = str(uuid.uuid4())+"__"+profile_pic.filename
        profile_pic_path = os.path.join(abs_profile_pics_path, pic_full_name)
        with open(profile_pic_path, "wb") as buffer:
            buffer.write(await profile_pic.read())
        profile_pic_path = os.path.join(profile_pics, pic_full_name) # Save relative path
    user_data = {
        "full_name": full_name,
        "email": email,
        "password": hashed_password,
        "profile_pic": profile_pic_path
    }

    db.users.insert_one(user_data)
    return {"message": "User registered successfully"}
