import os
from pathlib import Path
from fastapi import UploadFile

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def save_upload_file(upload_file: UploadFile):
    file_path = UPLOAD_DIR / upload_file.filename
    with open(file_path, "wb") as buffer:
        buffer.write(upload_file.file.read())
    return upload_file.filename, str(file_path)
