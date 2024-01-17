"""
Django settings for innverse project.
"""

from pathlib import Path
from os import environ as env
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = env.get("TWI_KEY")
if SECRET_KEY is None:
    raise Exception(
        "The secret key ('TWI_KEY\") must be available in the environment to run this application!"
    )

# DON'T RUN WITH DEBUG TURNED ON IN PRODUCTION!
TWI_DEBUG = env.get("TWI_DEBUG")
DEBUG = TWI_DEBUG is not None and (TWI_DEBUG == "1" or TWI_DEBUG.lower() == "true")
if DEBUG:
    X_FRAME_OPTIONS = "SAMEORIGIN"  # get detailed error pages from pattern library

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INTERNAL_IPS = ["127.0.0.1"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "innverse.core",
    "stats",
    "tailwind",
    "theme",
    "django_browser_reload",
    "pattern_library",
    "debug_toolbar",
    "django_tables2",
]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

ROOT_URLCONF = "innverse.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            Path(BASE_DIR, "innverse/core/templates/patterns"),
            Path(BASE_DIR, "innverse/core/templates/admin"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "builtins": ["pattern_library.loader_tags"],
        },
    },
]

ASGI_APPLICATION = "innverse.asgi.application"


# Database
CONN_MAX_AGE = 30
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "innverse",
        "USER": env.get("TWI_DB_USER", "postgres"),
        "PASSWORD": env.get("TWI_DB_PASS", "password"),
        "HOST": env.get("TWI_DB_HOST", "127.0.0.1"),
        "PORT": env.get("TWI_DB_PORT", "5432"),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = env.get("TWI_STATIC_URL", "static/")
STATIC_ROOT = env.get("TWI_STATIC_ROOT", "/tmp/twi-stats/static/")


# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"
    ]
}

TAILWIND_APP_NAME = "theme"


PATTERN_LIBRARY = {
    # Groups of templates for the pattern library navigation. The keys
    # are the group titles and the values are lists of template name prefixes that will
    # be searched to populate the groups.
    "SECTIONS": (
        ("atoms", ["patterns/atoms"]),
        ("molecules", ["patterns/molecules"]),
        ("pages", ["patterns/pages"]),
    ),
    # Configure which files to detect as templates.
    "TEMPLATE_SUFFIX": ".html",
    # Set which template components should be rendered inside of,
    # so they may use page-level component dependencies like CSS.
    "PATTERN_BASE_TEMPLATE_NAME": "patterns/base.html",
    # Any template in BASE_TEMPLATE_NAMES or any template that extends a template in
    # BASE_TEMPLATE_NAMES is a "page" and will be rendered as-is without being wrapped.
    "BASE_TEMPLATE_NAMES": ["patterns/base_page.html"],
}

CACHES = {
    "default": {
        # "LOCATION": env.get("CACHE_URI", "PROTO://IP:PORT"),
        # "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": 60,
        "OPTIONS": {"MAX_ENTRIES": 1000},
    }
}

# Production
TWI_PROD = env.get("TWI_PROD")
PROD = TWI_PROD is not None and (TWI_PROD == "1" or TWI_PROD.lower() == "true")
if PROD:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "./debug.log",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console", "file"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
