import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://dialer:dialer@localhost:5432/dialer"
)
MEDIA_DIR = os.getenv("MEDIA_DIR", "media")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))
PHOTO_SIZE = 512
