import os
from fastapi import UploadFile
from uuid import uuid4

UPLOAD_DIR = "uploads"


def save_upload_file(upload: UploadFile) -> tuple[str, str]:
    """
    Salva o arquivo enviado em disco e retorna (filename_original, path).
    O arquivo é salvo com nome único (uuid) para evitar colisões,
    mas o filename original é retornado separadamente para exibição.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    original_filename = upload.filename or "arquivo"
    ext = os.path.splitext(original_filename)[1]
    unique_name = f"{uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, unique_name)

    # Garante que lemos do início do buffer
    upload.file.seek(0)
    with open(path, "wb") as f:
        f.write(upload.file.read())

    # Retorna o nome original (para exibição) e o path real em disco
    return original_filename, path
