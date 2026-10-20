import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured")

# Hosts often hand out "postgres://" or "postgresql://"; SQLAlchemy needs a driver.
for prefix in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(prefix):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len(prefix):]
        break

MEDIA_DIR = os.getenv("MEDIA_DIR", "media")
MAX_UPLOAD_BYTES = int(
    os.getenv("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024))
)
PHOTO_SIZE = 512