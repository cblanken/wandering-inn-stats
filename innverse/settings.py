"""
Django settings for innverse project.
"""

from pathlib import Path
from os import environ as env
from dotenv import load_dotenv
import pymemcache  # type: ignore[import-untyped]
from typing import Any

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = env.get("TWI_KEY")
if SECRET_KEY is None:
    msg = "The secret key (TWI_KEY) must be available in the environment to run this application!"
    raise Exception(msg)

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    env.get("TWI_PUBLIC_HOST"),
    env.get("TWI_INTERNAL_HOST"),
    env.get("TWI_WIREGUARD_BASTION"),
]

INTERNAL_IPS = ["127.0.0.1"]

# HTTP Headers
USE_X_FORWARDED_HOST = True

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "django_browser_reload",
    "django_htmx",
    "django_minify_html",
    "django_tables2",
    "innverse",
    "innverse.core",
    "pattern_library",
    "rest_framework",
    "stats",
    "tailwind",
    "theme",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "django_minify_html.middleware.MinifyHtmlMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# DON'T RUN WITH DEBUG TURNED ON IN PRODUCTION!
TWI_DEBUG = env.get("TWI_DEBUG")
DEBUG = TWI_DEBUG is not None and (TWI_DEBUG == "1" or TWI_DEBUG.lower() == "true")
if DEBUG:
    X_FRAME_OPTIONS = "SAMEORIGIN"  # get detailed error pages from pattern library
    INSTALLED_APPS.append("debug_toolbar")
    INSTALLED_APPS.append("template_profiler_panel")
    INSTALLED_APPS.append("pyflame")

ROOT_URLCONF = "innverse.urls"

DEBUG_TOOLBAR_PANELS = [
    "debug_toolbar.panels.history.HistoryPanel",
    "debug_toolbar.panels.versions.VersionsPanel",
    "debug_toolbar.panels.timer.TimerPanel",
    "debug_toolbar.panels.settings.SettingsPanel",
    "debug_toolbar.panels.headers.HeadersPanel",
    "debug_toolbar.panels.request.RequestPanel",
    "debug_toolbar.panels.sql.SQLPanel",
    "debug_toolbar.panels.staticfiles.StaticFilesPanel",
    "debug_toolbar.panels.templates.TemplatesPanel",
    "debug_toolbar.panels.cache.CachePanel",
    "debug_toolbar.panels.signals.SignalsPanel",
    "debug_toolbar.panels.redirects.RedirectsPanel",
    "debug_toolbar.panels.profiling.ProfilingPanel",
    "template_profiler_panel.panels.template.TemplateProfilerPanel",
    "pyflame.djdt.panel.FlamegraphPanel",
]

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
                "innverse.context_processors.analytics",
                "innverse.context_processors.prod",
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
    },
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
STATIC_URL = env.get("TWI_STATIC_URL", "/static/")
STATIC_ROOT = env.get("TWI_STATIC_ROOT", "static/")  # noqa: S108

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"],
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

# Wiki Bot Configuration
TWIKI_BOT_USER = env.get("PYWIKIBOT_USER")
TWIKI_BOT_NAME = env.get("PYWIKIBOT_BOT_NAME")
TWIKI_BOT_PASS = env.get("PYWIKIBOT_PASS")
with Path.open(Path("user-password.py"), "w", encoding="utf-8") as fp:
    fp.write(f"('en', 'twi', {TWIKI_BOT_USER}, BotPassword('{TWIKI_BOT_NAME}', '{TWIKI_BOT_PASS}'))")


# Analytics env
ANALYTICS_ID = env.get("ANALYTICS_ID")

# Production
TWI_PROD = env.get("TWI_PROD")
PROD = TWI_PROD is not None and (TWI_PROD == "1" or TWI_PROD.lower() == "true")
if PROD:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


DISABLE_CACHE = env.get("TWI_DISABLE_CACHE", False)
CACHES: dict[str, str | dict[str, Any] | int | bool] = {}
if DISABLE_CACHE:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        },
    }
else:
    if TWI_PROD:
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
                "LOCATION": env.get("TWI_CACHE_URI", "127.0.0.1:11211"),
                "TIMEOUT": 300,
                "OPTIONS": {
                    "no_delay": True,
                    "ignore_exc": True,
                    "max_pool_size": 4,
                    "use_pooling": True,
                    "allow_unicode_keys": True,
                    "default_noreply": False,
                    "serde": pymemcache.serde.pickle_serde,
                },
            },
        }
    else:
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            },
        }
