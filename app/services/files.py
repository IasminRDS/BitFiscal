import uuid
import os
from fastapi import UploadFile

UPLOAD_DIR = "uploads"


async def save_upload_file_secure(file: UploadFile) -> tuple:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    safe_name = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(UPLOAD_DIR, safe_name)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return safe_name, path
