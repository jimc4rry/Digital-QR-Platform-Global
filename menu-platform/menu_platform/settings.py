import os
from pathlib import Path
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

# Absolute base URL used to build QR codes (e.g. https://menu.example.com)
SITE_URL = config('SITE_URL', default='http://127.0.0.1:8000').rstrip('/')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'crispy_forms',
    'crispy_bootstrap5',
    'storages',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',

    # Local
    'accounts',
    'restaurants',
    'orders',
    'api',

    # Must come after the apps whose models it cleans up media for.
    'django_cleanup.apps.CleanupConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'menu_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'restaurants.context_processors.restaurant_context',
                'accounts.context_processors.beta_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'menu_platform.wsgi.application'

# Database - SQLite for local dev by default. Set DATABASE_URL (e.g. postgres://...)
# to switch to Postgres in production without any code change.
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Global edition: English only. LocaleMiddleware activates 'en' for every
# request since it's the only entry in LANGUAGES, which renders every
# {% trans %}/{% blocktrans %} tag (and every gettext() call) in English
# using the translations already compiled into locale/en/LC_MESSAGES/django.mo.
LANGUAGES = [
    ('en', 'English'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files: local filesystem by default. Set AWS_STORAGE_BUCKET_NAME (+ credentials)
# to switch to S3-compatible storage (AWS S3, Cloudflare R2, DigitalOcean Spaces, ...)
# in production without any code change - required for any multi-instance/cloud deploy,
# since local disk storage doesn't survive redeploys or scale past one server.
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')

if AWS_STORAGE_BUCKET_NAME:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default=None)
    AWS_S3_CUSTOM_DOMAIN = config('AWS_S3_CUSTOM_DOMAIN', default=None)
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False

    # Django's STORAGES setting is not merged with the built-in defaults when
    # overridden - omitting 'staticfiles' here would silently break collectstatic.
    STORAGES = {
        'default': {'BACKEND': 'storages.backends.s3.S3Storage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }

# Authentication
AUTH_USER_MODEL = 'accounts.User'
LOGIN_REDIRECT_URL = 'post_login_redirect'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'login'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# REST API (used by the owner/staff mobile app - the customer-facing public menu
# and the web dashboard are untouched and keep using regular Django views).
from datetime import timedelta

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
}

# CORS: only needed so the Flutter app (running from a different origin - an emulator,
# a device on the LAN, or later a packaged app) can call the API. The web dashboard
# itself doesn't need this since it's served same-origin.
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',') if config('CORS_ALLOWED_ORIGINS', default='') else []

# CSRF: needed on top of ALLOWED_HOSTS whenever the dashboard is accessed through a
# different HTTPS origin than SITE_URL - e.g. an ngrok tunnel while testing the Paddle
# checkout/webhook locally, where Paddle requires a real (non-localhost) HTTPS domain.
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='').split(',') if config('CSRF_TRUSTED_ORIGINS', default='') else []

# Push notifications (mobile app): set FIREBASE_CREDENTIALS_PATH to a Firebase
# service-account JSON file to enable. Left unset, push is a silent no-op -
# same "inert until configured" pattern as the S3 media storage above.
FIREBASE_CREDENTIALS_PATH = config('FIREBASE_CREDENTIALS_PATH', default='')

# Beta mode: billing isn't live yet (e.g. waiting on Paddle production approval).
# Every account gets full access to every plan's features for free, and the
# checkout page shows a "beta" notice instead of a real Paddle checkout - see
# accounts.models.User.has_active_subscription/has_ordering/etc. Turn this off
# (and switch PADDLE_ENV to 'production' with production credentials) once
# billing should actually start charging people.
BETA_MODE = config('BETA_MODE', default=False, cast=bool)

# Paddle billing: Paddle.js embedded Checkout for upgrades, the Paddle
# customer portal for self-serve cancel/manage, webhook for the source of
# truth on plan/status. Paddle acts as Merchant of Record, so it handles
# international VAT/sales tax automatically - no separate tax integration
# needed. PADDLE_PRICE_PRO / PADDLE_PRICE_BUSINESS are filled in after running
# `manage.py sync_paddle_plans`. Left unset, checkout just 404s - same
# "inert until configured" pattern as Firebase/S3 above.
PADDLE_ENV = config('PADDLE_ENV', default='sandbox')  # 'sandbox' or 'production'
PADDLE_API_KEY = config('PADDLE_API_KEY', default='')
PADDLE_CLIENT_TOKEN = config('PADDLE_CLIENT_TOKEN', default='')
PADDLE_WEBHOOK_SECRET = config('PADDLE_WEBHOOK_SECRET', default='')
PADDLE_PRICE_BASIC = config('PADDLE_PRICE_BASIC', default='')
PADDLE_PRICE_PRO = config('PADDLE_PRICE_PRO', default='')
PADDLE_PRICE_BUSINESS = config('PADDLE_PRICE_BUSINESS', default='')

# Email settings (development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# File upload limits (protect against decompression-bomb / DoS uploads)
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MB

# Security hardening (only meaningful once deployed behind HTTPS)
if not DEBUG:
    # Railway (and most PaaS hosts) terminate TLS at their edge proxy and forward
    # the request to us as plain HTTP - without this, Django can't tell the
    # original request was HTTPS and SECURE_SSL_REDIRECT below causes an
    # infinite redirect loop.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'