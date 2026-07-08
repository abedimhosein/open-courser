from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Ensure ffmpeg/ffprobe (installed via WinGet) is in PATH
_winget_links = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links")
if os.path.isdir(_winget_links) and _winget_links not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _winget_links + os.pathsep + os.environ.get("PATH", "")

SECRET_KEY = "django-insecure-0@0i4f9-un1#lc0!*!ji(9^$s&s&g*-tvfaju*2cyp(a@hwxq@"

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.workspaces",
    "apps.courses",
    "apps.media",
    "apps.progress",
    "apps.notes",
]

if DEBUG:
    INSTALLED_APPS.insert(0, "debug_toolbar")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

INTERNAL_IPS = ["127.0.0.1"]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "opencourser"),
        "USER": os.environ.get("POSTGRES_USER", "opencourser"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "opencourser"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = []

USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Course root directories (indexed env vars from .env)
COURSE_ROOTS = []
_i = 0
while True:
    _root = os.environ.get(f"COURSE_ROOT_{_i}")
    if _root is None:
        break
    COURSE_ROOTS.append({
        "host_path": _root,
        "container_path": f"/courses/{_i}",
    })
    _i += 1
