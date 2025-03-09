from fastapi import APIRouter, HTTPException, Form
import jwt
import datetime
from pydantic import BaseModel, EmailStr
from cdots.core.config import SECRET_KEY, ALGORITHM, pwd_context
from cdots.db.mongo.mongo_connection import MongoDBConnection

router = APIRouter(prefix="/api/v1", tags=["User Authentication"])

# Initialize MongoDB connection
db_connection = MongoDBConnection()
db = db_connection.get_db()

# Utility function to create JWT token
def create_access_token(email, user_id):
    payload = {
        "sub": email,
        "user_id": str(user_id),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

### **1️⃣ Pydantic Schema for Swagger**
class LoginResponse(BaseModel):
    message: str
    user_id: str
    email: EmailStr
    full_name: str
    profile_pic: str | None
    access_token: str

### **2️⃣ Login Endpoint with Swagger Docs**
@router.post("/login/", response_model=LoginResponse, summary="User Login", description="Authenticate user and return JWT token.")
async def login_user(
    email: EmailStr = Form(..., description="User's email address"),
    password: str = Form(..., description="User's password")
):
    """
    **Login API**
    - Requires: `email`, `password`
    - Returns: **JWT Token**, `user_id`, `full_name`, `profile_pic`
    """
    user = db.users.find_one({"email": email})

    if not user or not pwd_context.verify(password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(user["email"], user["_id"])

    return {
        "message": "Login successful",
        "user_id": str(user["_id"]),
        "email": user["email"],
        "full_name": user["full_name"],
        "profile_pic": user.get("profile_pic", None),
        "access_token": token
    }
