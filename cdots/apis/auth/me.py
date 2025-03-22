from fastapi import APIRouter, Depends, HTTPException
from cdots.db.mongo.mongo_connection import MongoDBConnection
from cdots.apis.auth.utils import get_current_user

router = APIRouter(prefix="/api/v1", tags=["User Profile"])

# MongoDB setup
db_connection = MongoDBConnection()
db = db_connection.get_db()

@router.get("/me")
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Returns the profile of the currently logged-in user.
    """

    user = db.users.find_one(
        {"_id": current_user["user_id"]},
        {"full_name": 1, "email": 1, "profile_pic": 1, "t__created_at": 1}
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": str(current_user["user_id"]),
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "profile_pic": user.get("profile_pic"),
        "t__created_at": user.get("created_at")
    }
