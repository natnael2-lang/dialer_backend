import hashlib
import io
import os
import uuid

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps

from .config import MAX_UPLOAD_BYTES, MEDIA_DIR, PHOTO_SIZE

Image.MAX_IMAGE_PIXELS = 50_000_000


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def save_photo(file: UploadFile) -> str:
    """Validate, auto-rotate, center-crop to a square, shrink and re-encode as
    progressive JPEG (~30-60 KB). Returns the stored filename."""
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Photo is too large (max 8 MB)")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise HTTPException(400, "That file is not a valid image")

    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageOps.fit(img, (PHOTO_SIZE, PHOTO_SIZE), Image.LANCZOS)

    os.makedirs(MEDIA_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    img.save(
        os.path.join(MEDIA_DIR, filename),
        "JPEG",
        quality=82,
        optimize=True,
        progressive=True,
    )
    return filename


def delete_photo(filename: str | None) -> None:
    if not filename:
        return
    try:
        os.remove(os.path.join(MEDIA_DIR, os.path.basename(filename)))
    except FileNotFoundError:
        pass
