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
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))
PHOTO_SIZE = 512

# Shared secret the phone app sends when looking up an incoming caller.
APP_KEY = os.getenv("APP_KEY", "dev-app-key")

# Password for the /admin dashboard. Set this in Render.
ADMIN_KEY = os.getenv("ADMIN_KEY", "admin")

# Public URL of this server, e.g. https://dialer-backend-og10.onrender.com
# Used to build photo URLs. Render sits behind a proxy, so without this the
# URLs can come out as http:// and Android will refuse to load them.
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

# Login throttle: failures allowed per (ip, chat ID) inside the window.
LOGIN_MAX_FAILS = int(os.getenv("LOGIN_MAX_FAILS", "8"))
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "600"))
