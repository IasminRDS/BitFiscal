import os
from fastapi import UploadFile
from uuid import uuid4

UPLOAD_DIR = "uploads"


def save_upload_file(upload: UploadFile) -> (str, str):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(upload.filename)[1]
    filename = f"{uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(upload.file.read())
    return filename, path
