from fastapi import FastAPI, File, UploadFile
import os

# Create FastAPI app
app = FastAPI(
    title="CDOTS",
    description="🚀 A high-performance API built using FastAPI for CDOTS.",
    version="2.0.0",
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

# Ensure 'uploads' directory exists
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    # Save file to disk
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    return {"filename": file.filename, "saved_to": file_path}

# Run the app: uvicorn main:app --reload
