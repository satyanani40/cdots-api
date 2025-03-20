from fastapi import APIRouter, HTTPException, Form, UploadFile, File, Depends, Security
from fastapi.security import OAuth2PasswordBearer
import os
import cv2
import numpy as np
from bson import ObjectId
from cdots.core.config import SECRET_KEY
from cdots.db.mongo.mongo_connection import MongoDBConnection
from cdots.core.face_analysis import FaceAppSingleton
from cdots.apis.auth.utils import get_current_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

router = APIRouter(prefix="/api/v1", tags=["Family Tree"])

db_connection = MongoDBConnection()
db = db_connection.get_db()
face_app = FaceAppSingleton.get_instance()

UPLOAD_FOLDER = "uploads/profile_pics"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.post("/create-family-tree")
async def create_family_tree(
        tree_name: str = Form(...),
        mode: str = Form(..., description="'self' for logged-in user, 'custom' for another user"),
        full_name: str = Form(None),  # Required if mode="custom"
        email: str = Form(None),  # Required if mode="custom"
        profile_pic: UploadFile = File(None),  # Required if mode="custom"
        current_user: dict = Depends(get_current_user)
):
    """
    Creates a family tree based on mode:
    - **self** → Creates a tree with the logged-in user as the first member.
    - **custom** → Creates a tree for another user (requires `full_name`, `email`, `profile_pic`).
    """

    # Validate mode
    if mode not in ["self", "custom"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'self' or 'custom'.")

    # If mode is "self", use logged-in user details
    if mode == "self":
        full_name = current_user["full_name"]
        email = current_user["email"]

        # Check if user already has a family tree
        existing_user = db.users.find_one({"email": email})
        if existing_user and "family_trees" in existing_user and existing_user["family_trees"]:
            raise HTTPException(status_code=400, detail="User is already part of a family tree.")

    # If mode is "custom", ensure required fields are provided
    elif mode == "custom":
        if not full_name or not email or not profile_pic:
            raise HTTPException(status_code=400,
                                detail="Full name, email, and profile pic are required for custom mode.")

        # Check if the custom user already exists in any tree
        existing_user = db.users.find_one({"email": email})
        if existing_user and "family_trees" in existing_user and existing_user["family_trees"]:
            raise HTTPException(status_code=400, detail="User is already part of a family tree.")

    # Handle profile picture (Required for 'custom', Optional for 'self')
    profile_pic_path = None
    if profile_pic:
        profile_pic_path = os.path.join(UPLOAD_FOLDER, profile_pic.filename)
        with open(profile_pic_path, "wb") as buffer:
            buffer.write(await profile_pic.read())

    # Generate face embedding if profile picture is uploaded
    face_embedding = None
    if profile_pic:
        img = face_app.get(cv2.imread(profile_pic_path))
        if not img:
            raise HTTPException(status_code=400, detail="No face detected in the image")
        face_embedding = img[0].embedding.tolist()

    # Create new family tree
    tree_data = {
        "tree_name": tree_name,
        "created_by": current_user["user_id"],
        "members": [{
            "user_id": None,
            "full_name": full_name,
            "email": email,
            "profile_pic": profile_pic_path,
            "relation_name": "self",
            "children": []
        }]
    }
    inserted_tree = db.family_trees.insert_one(tree_data)
    tree_id = inserted_tree.inserted_id

    # Insert user in `users` collection
    user_data = {
        "full_name": full_name,
        "email": email,
        "profile_pic": profile_pic_path,
        "family_trees": [str(tree_id)]
    }
    inserted_user = db.users.insert_one(user_data)
    user_id = inserted_user.inserted_id

    # Update tree with user ID
    db.family_trees.update_one(
        {"_id": tree_id, "members.email": email},
        {"$set": {"members.$.user_id": str(user_id)}}
    )

    # Store face embedding separately if available
    if face_embedding:
        db.users_face_embeddings.insert_one({
            "_id": user_id,
            "user_id": str(user_id),
            "face_embedding": face_embedding
        })

    return {
        "message": "Family tree created successfully",
        "family_tree_id": str(tree_id),
        "user_id": str(user_id),
        "email": email
    }
