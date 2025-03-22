import datetime
import uuid
import os
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Depends, Form, UploadFile, File
from pydantic import BaseModel, EmailStr, Field

from cdots.core.config import SECRET_KEY, ALGORITHM, pwd_context
from cdots.db.mongo.mongo_connection import MongoDBConnection
from cdots.core.config import MONGO_URI, MONGO_DB_NAME
from cdots.core.config import STATIC_FOLDER_PATH
from cdots.core.face_analysis import FaceAppSingleton
from cdots.core.utils import get_unique_mongo_id

router = APIRouter(prefix="/api/v1", tags=["User Authentication"])

# Initialize FaceApp
face_app = FaceAppSingleton.get_instance()

# MongoDB setup
db_connection = MongoDBConnection(uri=MONGO_URI, db_name=MONGO_DB_NAME)
db = db_connection.get_db()

# Folder setup
profile_pics = "profile_pics"
abs_profile_pics_path = os.path.join(STATIC_FOLDER_PATH, profile_pics)
os.makedirs(abs_profile_pics_path, exist_ok=True)

# Util: Normalize embedding
def l2_normalize(vec):
    vec = np.array(vec)
    norm_val = np.linalg.norm(vec)
    return (vec / norm_val).tolist() if norm_val != 0 else vec.tolist()


class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=1, description="Full name cannot be empty")
    email: EmailStr = Field(..., description="Valid email required")
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    re_enter_password: str = Field(..., min_length=6, description="Passwords must match", alias="re_enter_password")
    profile_pic: UploadFile = File(None)


@router.post("/register")
async def register_user(
        full_name: str = Form(...),
        email: EmailStr = Form(...),
        password: str = Form(..., min_length=6),
        re_enter_password: str = Form(..., min_length=6, alias="re_enter_password"),
        profile_pic: UploadFile = File(None)
):
    if password != re_enter_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    existing_user = db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    if not profile_pic:
        raise HTTPException(status_code=400, detail="Profile picture is required")

    # Step 1: Read image from memory
    img_bytes = await profile_pic.read()
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Step 2: Detect face
    faces = face_app.get(img)
    if not faces:
        raise HTTPException(status_code=400, detail="No face detected in the uploaded image")

    # Step 3: Select largest face and crop
    faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
    face = faces[0]
    x1, y1, x2, y2 = [int(i) for i in face.bbox]
    cropped_face = img[y1:y2, x1:x2]

    if cropped_face.size == 0:
        raise HTTPException(status_code=400, detail="Cropped face is empty or invalid")

    # Step 4: Resize to 112x112 (ArcFace default)
    cropped_face_resized = cv2.resize(cropped_face, (112, 112))

    # Step 5: Save cropped face to disk
    pic_full_name = str(uuid.uuid4())+"__"+profile_pic.filename
    #str(uuid.uuid4()) + "__cropped.jpg"
    abs_profile_pic_path = os.path.join(abs_profile_pics_path, pic_full_name)
    with open(abs_profile_pic_path, "wb") as buffer:
        buffer.write(await profile_pic.read())
    profile_pic_path = os.path.join(profile_pics, pic_full_name)  # Relative for DB

    #cv2.imwrite(abs_profile_pic_path, cropped_face_resized)

    # Step 6: Extract and normalize embedding
    raw_embedding = face.embedding
    face_embedding = l2_normalize(raw_embedding)

    # Step 7: Save user
    user_id = get_unique_mongo_id()
    user_data = {
        "_id": user_id,
        "full_name": full_name,
        "email": email,
        "password": pwd_context.hash(password),
        "profile_pic": profile_pic_path,
        "t__created_at": datetime.datetime.now()

    }
    db.users.insert_one(user_data)

    # Step 8: Save embedding
    db.users_face_embeddings.insert_one({
        "_id": user_id,
        "user_id": str(user_id),
        "face_embedding": face_embedding
    })

    return {
        "message": "User registered successfully",
        "user_id": str(user_id),
        "email": email,
        "profile_pic": profile_pic_path
    }
