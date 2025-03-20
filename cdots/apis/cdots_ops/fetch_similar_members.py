from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi import APIRouter, HTTPException, Form, UploadFile, File, Depends, Security
import cv2
import numpy as np
from numpy.linalg import norm
from bson.objectid import ObjectId
from cdots.db.mongo.mongo_connection import MongoDBConnection
from cdots.core.face_analysis import FaceAppSingleton  # Import centralized FaceAnalysis

from cdots.apis.auth.utils import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Member Operations"])

# Initialize MongoDB connection
db_connection = MongoDBConnection()
db = db_connection.get_db()

# Use the shared face analysis instance
face_app = FaceAppSingleton.get_instance()

@router.post("/fetch-similar-members-by-pic")
async def add_member(profile_pic: UploadFile = File(...),
                     current_user: dict = Depends(get_current_user)):
    """
    Uploads a picture, extracts face embedding, and finds the top 100 matches without saving the image.
    """
    # Read the image from memory
    contents = await profile_pic.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Get face embedding
    detected_faces = face_app.get(img)
    if not detected_faces:
        raise HTTPException(status_code=400, detail="No face detected in the image")

    uploaded_embedding = detected_faces[0].embedding.tolist()

    # MongoDB Aggregation Query: Compute similarity in MongoDB without fetching all documents
    pipeline = [
        {
            "$project": {
                "user_id": 1,
                "face_embedding": 1,
                "match_percentage": {
                    "$subtract": [1, {
                        "$sqrt": {
                            "$sum": [
                                {"$pow": [
                                    {"$subtract": [{"$arrayElemAt": ["$face_embedding", i]}, uploaded_embedding[i]]},
                                    2]}
                                for i in range(512)  # Loop over all 512 dimensions
                            ]
                        }
                    }]
                }
            }
        },
        {"$sort": {"match_percentage": -1}},
        {"$limit": 100}
    ]

    print(pipeline)

    matches = list(db.users_face_embeddings.aggregate(pipeline))

    # Fetch matched user details from `users` collection
    matched_users = []
    for match in matches:
        user = db.users.find_one({"_id": match["user_id"]}, {"full_name": 1, "email": 1, "profile_pic": 1})
        if user:
            matched_users.append({
                "user_id": str(user["_id"]),
                "full_name": user["full_name"],
                "email": user["email"],
                "profile_pic": user.get("profile_pic"),
                "match_percentage": round(match["match_percentage"] * 100, 2)
            })

    return {
        "message": "Face recognition completed",
        "matched_users": matched_users
    }
