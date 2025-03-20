from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
import jwt
from cdots.core.config import SECRET_KEY, ALGORITHM
from cdots.db.mongo.mongo_connection import MongoDBConnection
from cdots.core.logging_config import get_logger

logger = get_logger()

# OAuth2 Password Bearer token setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

# Initialize MongoDB connection
db_connection = MongoDBConnection()
db = db_connection.get_db()


def get_current_user(token: str = Security(oauth2_scheme)):
    """
    Validates and decodes the JWT token to retrieve the logged-in user.
    """
    try:
        token = token.split(" ")[-1]
        logger.debug(f"get current user token:{token}")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        user = db.users.find_one({"_id": str(user_id)}, {"full_name": 1, "email": 1})

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return {"user_id": str(user["_id"]), "full_name": user["full_name"], "email": user["email"]}

    except jwt.ExpiredSignatureError as e:
        logger.warning(f"token expired, info:{e}")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"token expired, info:{e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.warning(f"token expired, info:{e}")
        raise HTTPException(status_code=401, detail="Invalid token")
