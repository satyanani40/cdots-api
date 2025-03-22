from fastapi import APIRouter, HTTPException, Form, Depends
from cdots.db.mongo.mongo_connection import MongoDBConnection
from cdots.apis.auth.utils import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Relationships"])

db_connection = MongoDBConnection()
db = db_connection.get_db()

def add_child_recursive(members, parent_id, new_child):
    for member in members:
        if member["user_id"] == parent_id:
            if "children" not in member:
                member["children"] = []
            member["children"].append(new_child)
            return True
        if "children" in member:
            if add_child_recursive(member["children"], parent_id, new_child):
                return True
    return False


@router.post("/add-family-member")
async def add_family_member(
    tree_id: str = Form(...),
    user_id: str = Form(...),
    parent_user_id: str = Form(...),
    relation_name: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    existing_user = db.users.find_one({"_id": user_id})
    if not existing_user:
        raise HTTPException(status_code=400, detail="Adding User Not Exists")

    parent_user = db.users.find_one({"_id": parent_user_id})
    if not parent_user:
        raise HTTPException(status_code=400, detail="Parent User Not Exists")


    tree = db.family_trees.find_one({"_id": tree_id})
    if not tree:
        raise HTTPException(status_code=404, detail="Family tree not found")

    members = tree["members"]

    # Prepare new child entry
    new_child = {
        "user_id": user_id,
        "relation_name": relation_name,
        "children": []  # Optional: to allow adding grandchildren
    }

    # Recursively find and insert
    inserted = add_child_recursive(members, parent_user_id, new_child)

    if not inserted:
        raise HTTPException(status_code=400, detail="Parent not found in tree members")

    # Save updated tree
    db.family_trees.update_one({"_id": tree_id}, {"$set": {"members": members}})

    return {
        "message": "Family member added successfully",
        "user_id": user_id,
        "relation_name": relation_name
    }

@router.post("/connect-family-trees/")
async def connect_family_trees(
    tree_1_id: str = Form(...),
    tree_2_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    tree_1 = db.family_trees.find_one({"_id": tree_1_id})
    tree_2 = db.family_trees.find_one({"_id": tree_2_id})

    if not tree_1 or not tree_2:
        raise HTTPException(status_code=404, detail="One or both family trees not found")

    db.family_trees.update_one(
        {"_id": tree_1_id},
        {"$addToSet": {"connected_trees": tree_2_id}}
    )

    db.family_trees.update_one(
        {"_id": tree_2_id},
        {"$addToSet": {"connected_trees": tree_1_id}}
    )

    return {
        "message": "Family trees connected successfully",
        "tree_1_id": tree_1_id,
        "tree_2_id": tree_2_id
    }
