from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-me')
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',
    'django_filters',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'graphene_django',
    'groby',
]

GRAPHENE = {
    'SCHEMA': 'groby.schema.schema',
}

VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_CLAIM_EMAIL = os.getenv('VAPID_CLAIM_EMAIL', 'admin@example.com')

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticatedOrReadOnly'],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/hour',
        'user': '1000/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Informator Cmentarny — Szydłów API',
    'DESCRIPTION': 'REST API do bazy grobów cmentarza parafialnego w Szydłowie.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {'email': 'admin@example.com'},
    'LICENSE': {'name': 'MIT'},
}

# Redis cache (opcjonalny, gdy DJANGO_REDIS_URL ustawione)
if os.getenv('DJANGO_REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv('DJANGO_REDIS_URL'),
        }
    }

# PostgreSQL przez DATABASE_URL (np. postgres://user:pass@host/db)
if os.getenv('DATABASE_URL'):
    import urllib.parse
    urllib.parse.uses_netloc.append('postgres')
    u = urllib.parse.urlparse(os.getenv('DATABASE_URL'))
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': u.path[1:],
        'USER': u.username,
        'PASSWORD': u.password,
        'HOST': u.hostname,
        'PORT': u.port or 5432,
    }

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'groby-cache',
    }
}

# Security — aktywne tylko gdy DEBUG=False
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    SECURE_HSTS_SECONDS = 31536000  # 1 rok
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'
    SESSION_COOKIE_SECURE = os.getenv('DJANGO_SECURE_COOKIE', 'False') == 'True'
    CSRF_COOKIE_SECURE = os.getenv('DJANGO_SECURE_COOKIE', 'False') == 'True'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'groby.middleware.BiezacyUzytkownikMiddleware',
    'groby.middleware.SecurityHeadersMiddleware',
]

LOGIN_URL = 'groby:logowanie'
LOGIN_REDIRECT_URL = 'groby:profil'
LOGOUT_REDIRECT_URL = 'groby:home'

EMAIL_BACKEND = os.getenv('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@cmentarz.szydlow.pl')

# Sentry — opcjonalne, aktywne tylko gdy ustawiono SENTRY_DSN.
SENTRY_DSN = os.getenv('SENTRY_DSN', '').strip()
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_RATE', '0.1')),
            send_default_pii=False,
        )
    except ImportError:
        pass  # sentry-sdk nie zainstalowane — pomiń

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'groby.context_processors.banner_kontekst',
                'groby.context_processors.featured_kontekst',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pl'
LANGUAGES = [
    ('pl', 'Polski'),
    ('en', 'English'),
    ('uk', 'Українська'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Europe/Warsaw'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Skan planu cmentarza wyświetlany na zakładce „Mapa”.
# Domyślnie używamy zeskanowanego planu z oznaczeniami sektorów/rzędów.
PLAN_IMAGE = os.getenv('PLAN_IMAGE', 'plan_cmentarza/scan_oznaczenia.jpg').strip()
PLAN_BOUNDS_RAW = os.getenv('PLAN_BOUNDS', '').strip()
PLAN_OPACITY = float(os.getenv('PLAN_OPACITY', '1.0'))
