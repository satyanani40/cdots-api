from fastapi import APIRouter, HTTPException, Form, UploadFile, File, Depends, Security
from fastapi.security import OAuth2PasswordBearer
import os
import cv2
import uuid
import numpy as np
from bson import ObjectId
from enum import Enum
from typing import Optional


from cdots.core.config import SECRET_KEY
from cdots.core.config import STATIC_FOLDER_PATH
from cdots.db.mongo.mongo_connection import MongoDBConnection
from cdots.core.face_analysis import FaceAppSingleton
from cdots.apis.auth.utils import get_current_user
from cdots.core.utils import get_unique_mongo_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

router = APIRouter(prefix="/api/v1", tags=["Family Tree"])

db_connection = MongoDBConnection()
db = db_connection.get_db()
face_app = FaceAppSingleton.get_instance()

UPLOAD_FOLDER = "uploads/profile_pics"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class ModeEnum(str, Enum):
    self_user = "self"
    custom = "custom"

@router.post("/create-family-tree")
async def create_family_tree(
        tree_name: str = Form(...),
        user_id: str = Form(None),  # Required if mode="custom"
        current_user: dict = Depends(get_current_user)
):
    # Check if user already has a family tree
    if user_id:
        existing_user = db.users.find_one({"_id": user_id})
    else:
        existing_user = db.users.find_one({"email": current_user["email"]})
    if not existing_user:
        raise HTTPException(status_code=400,
                            detail="User Should Be Registered before creating any family tree.")

    email = current_user["email"]

    # Create new family tree
    tree_data = {
        "tree_name": tree_name,
        "_id": get_unique_mongo_id(),
        "created_by": current_user["user_id"],
        "members": [{
            "user_id": existing_user['_id'],
            "relation_name": "self",
            "children": []
        }]
    }
    inserted_tree = db.family_trees.insert_one(tree_data)
    tree_id = inserted_tree.inserted_id
    user_id = existing_user['_id']
    return {
        "message": "Family tree created successfully",
        "family_tree_id": str(tree_id),
        "user_id": str(user_id),
        "email": email
    }
