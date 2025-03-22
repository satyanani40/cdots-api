import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from cdots.db.mongo.mongo_connection import MongoDBConnection
from cdots.core.face_analysis import FaceAppSingleton
from cdots.apis.auth.utils import get_current_user
import uuid
import os

router = APIRouter(prefix="/api/v1", tags=["Member Operations"])

# Initialize MongoDB connection
db_connection = MongoDBConnection()
db = db_connection.get_db()

# Shared face analysis instance
face_app = FaceAppSingleton.get_instance()

# Helper function to normalize embedding
def l2_normalize(vec):
    vec = np.array(vec)
    norm_val = np.linalg.norm(vec)
    return (vec / norm_val).tolist() if norm_val != 0 else vec.tolist()

@router.post("/fetch-similar-members-by-pic")
async def fetch_similar_members_by_pic(
        profile_pic: UploadFile = File(...),
        current_user: dict = Depends(get_current_user)):
    """
    Uploads a picture, crops and aligns the face, extracts embedding, and finds the top 100 matches.
    """

    # Step 1: Read and decode image
    contents = await profile_pic.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image format")

    # Step 2: Detect faces
    detected_faces = face_app.get(img)
    if not detected_faces:
        raise HTTPException(status_code=400, detail="No face detected in the image")

    # Step 3: Crop the largest face
    detected_faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
    face = detected_faces[0]
    x1, y1, x2, y2 = map(int, face.bbox)
    cropped_face = img[y1:y2, x1:x2]

    if cropped_face.size == 0:
        raise HTTPException(status_code=400, detail="Cropped face is empty or invalid")

    # Step 4: Resize cropped face for consistency (112x112 recommended for ArcFace)
    cropped_face_resized = cv2.resize(cropped_face, (112, 112))

    # Optional: Save for debugging
    debug_path = f"/mnt/git/cdots/{uuid.uuid4()}__debug_face.jpg"
    cv2.imwrite(debug_path, cropped_face_resized)

    # Step 5: Extract and normalize face embedding
    raw_embedding = face.embedding
    face_embedding = l2_normalize(raw_embedding)

    # Step 6: Build cosine similarity pipeline
    pipeline = [
        {
            "$project": {
                "user_id": 1,
                "face_embedding": 1,
                "dot_product": {
                    "$sum": [
                        {"$multiply": [{"$arrayElemAt": ["$face_embedding", i]}, face_embedding[i]]}
                        for i in range(512)
                    ]
                }
            }
        },
        {
            "$addFields": {
                "match_percentage": { "$multiply": ["$dot_product", 100] }
            }
        },
        {
            "$match": {
                "match_percentage": {"$gt": 30}  #  Only include scores > 60
            }
        },
        { "$sort": { "match_percentage": -1 } },
        { "$limit": 100 }
    ]

    matches = list(db.users_face_embeddings.aggregate(pipeline))

    # Step 7: Fetch matched user info from `users` collection
    matched_users = []
    for match in matches:
        user = db.users.find_one({"_id": match["user_id"]}, {"full_name": 1, "email": 1, "profile_pic": 1})
        if user:
            # Get all family trees for this user
            trees = db.family_trees.find({"created_by": str(user["_id"])}, {"tree_name": 1})
            user_family_trees = [{"tree_name": t["tree_name"]} for t in trees]

            matched_users.append({
                "user_id": str(user["_id"]),
                "full_name": user.get("full_name"),
                "email": user.get("email"),
                "profile_pic": user.get("profile_pic"),
                "match_percentage": round(match["match_percentage"], 2),
                "family_trees": user_family_trees  # include family trees here
            })

    return {
        "message": "Face recognition completed",
        "matched_users": matched_users
    }
