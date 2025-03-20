from bson import ObjectId

def get_unique_mongo_id():
    obj_id = ObjectId()
    return str(obj_id)
