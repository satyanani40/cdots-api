from pymongo import MongoClient



class MongoDBConnection:
    _instance = None

    def __new__(cls, uri="mongodb://localhost:27017/", db_name="cdots"):
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
            cls._instance.client = MongoClient(uri)
            cls._instance.db = cls._instance.client[db_name]
        return cls._instance

    def get_db(self):
        return self.db
