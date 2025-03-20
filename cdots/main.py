from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.openapi.models import Response as OpenAPIResponse
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from pymongo import MongoClient
import cv2
import json
import numpy as np
import os
import urllib
from insightface.app import FaceAnalysis
from numpy.linalg import norm
from typing import List
from fastapi.openapi.models import SecuritySchemeType
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware


from cdots.core.logging_config import get_logger

logger = get_logger()

#  Configure OAuth2 with Bearer Token (Fix Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


# Create FastAPI app
app = FastAPI(
    title="CDOTS",
    description="A high-performance API built using FastAPI for CDOTS.",
    version="1.0.0",
    contact={
        "name": "CDOTS Support",
        "url": "https://cdots.example.com",
        "email": "support@cdots.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# Ensure 'uploads' and 'data' directories exist
UPLOAD_FOLDER = "uploads"
DATA_FILE = "/mnt/git/cdots/data/embeddings.json"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("data", exist_ok=True)

# Load ArcFace model
face_app = FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0)

# Enable CORS if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



#  Custom OpenAPI function to register OAuth2 in Swagger UI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter 'Bearer <your_token>'"
        }
    }

    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Load existing embeddings
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        embeddings_data = json.load(f)
else:
    embeddings_data = []

@app.on_event("startup")
async def startup_event():
    logger.info("CDOTS Family Tree API has started!")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("CDOTS Family Tree API is shutting down!")


# Include API routers
from cdots.apis.auth.register import router as register_router
from cdots.apis.auth.login import router as login_router
from cdots.apis.cdots_ops.fetch_similar_members import router as fetch_similar_members_router
from cdots.apis.cdots_ops.family_tree import router as family_tree_route
from cdots.apis.cdots_ops.relationships import router as relationship_route

app.include_router(register_router)
app.include_router(login_router)
app.include_router(family_tree_route)
app.include_router(relationship_route)
app.include_router(fetch_similar_members_router)


@app.post("/upload/", summary="Upload an image and detect relations",
          response_description="Returns suggested relations",
          responses={200: {"description": "Image uploaded successfully"}, 400: {"description": "No face detected"}})
async def upload_image(person_name: str, relation_to: str, relation_type: str, file: UploadFile = File(...)):
    """
    Uploads an image and detects if the face matches any existing person in the file storage.
    If a match is found, it suggests possible relations.
    """
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Load and process image
    img = cv2.imread(file_path)
    faces = face_app.get(img)
    if not faces:
        return JSONResponse(status_code=400, content={"detail": "No face detected in the image."})

    embedding = faces[0].embedding.tolist()  # Convert numpy array to list

    # Search for matching faces in stored embeddings
    matching_persons = []
    for record in embeddings_data:
        stored_embedding = np.array(record["embedding"])
        distance = norm(stored_embedding - np.array(embedding))
        print(f"matched distance:{distance}")
        if distance < 0.6:  # ArcFace similarity threshold
            matching_persons.append({
                "name": record["name"],
                "relation": record["relation_to"],
                "relation_type": record.get("relation_type", "Unknown")
            })

    # Save new person to file
    new_record = {
        "name": person_name,
        "relation_to": relation_to,
        "relation_type": relation_type,
        "embedding": embedding,
        "image_path": file_path
    }
    embeddings_data.append(new_record)
    with open(DATA_FILE, "w") as f:
        json.dump(embeddings_data, f, indent=4)

    return {"message": "Image uploaded and processed successfully.", "suggested_relations": matching_persons}


@app.get("/family-tree/{person_name}", summary="Retrieve a person's family tree",
         response_description="Returns a list of family relations")
def get_family_tree(person_name: str):
    """
    Retrieves the family tree for a given person based on stored relationships in the file storage.
    """
    person = next((p for p in embeddings_data if p["name"] == person_name), None)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found.")

    relations = [p for p in embeddings_data if p["relation_to"] == person_name]

    return {"name": person_name, "family_relations": relations}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
