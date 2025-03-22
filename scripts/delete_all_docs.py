from pymongo import MongoClient

# MongoDB connection URI (modify as needed)
MONGO_URI = "mongodb://localhost:27017/"

# Name of the database you want to clean
DATABASE_NAME = "cdots"

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]

# Loop through all collections and delete documents
for collection_name in db.list_collection_names():
    if collection_name not in ['users1']:
        collection = db[collection_name]
        result = collection.delete_many({})
        print(f"Deleted {result.deleted_count} documents from '{collection_name}' collection.")

print("✅ All documents deleted from all collections.")
