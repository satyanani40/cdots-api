from fastapi import APIRouter, HTTPException, Form, Depends
from bson import ObjectId
from cdots.db.mongo.mongo_connection import MongoDBConnection
from cdots.apis.auth.utils import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Relationships"])

db_connection = MongoDBConnection()
db = db_connection.get_db()

@router.post("/add-family-member")
async def add_family_member(
    tree_id: str = Form(...),
    parent_user_id: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    relation_name: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    existing_user = db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    tree = db.family_trees.find_one({"_id": ObjectId(tree_id)})
    if not tree:
        raise HTTPException(status_code=404, detail="Family tree not found")

    user_data = {
        "full_name": full_name,
        "email": email,
        "family_trees": [tree_id]
    }
    inserted_user = db.users.insert_one(user_data)
    user_id = inserted_user.inserted_id

    db.family_trees.update_one(
        {"_id": ObjectId(tree_id), "members.user_id": parent_user_id},
        {"$push": {"members.$.children": {"user_id": str(user_id), "relation_name": relation_name}}}
    )

    return {
        "message": "Family member added successfully",
        "user_id": str(user_id),
        "relation_name": relation_name
    }

@router.post("/connect-family-trees/")
async def connect_family_trees(
    tree_1_id: str = Form(...),
    tree_2_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    tree_1 = db.family_trees.find_one({"_id": ObjectId(tree_1_id)})
    tree_2 = db.family_trees.find_one({"_id": ObjectId(tree_2_id)})

    if not tree_1 or not tree_2:
        raise HTTPException(status_code=404, detail="One or both family trees not found")

    db.family_trees.update_one(
        {"_id": ObjectId(tree_1_id)},
        {"$addToSet": {"connected_trees": ObjectId(tree_2_id)}}
    )

    db.family_trees.update_one(
        {"_id": ObjectId(tree_2_id)},
        {"$addToSet": {"connected_trees": ObjectId(tree_1_id)}}
    )

    return {
        "message": "Family trees connected successfully",
        "tree_1_id": tree_1_id,
        "tree_2_id": tree_2_id
    }
