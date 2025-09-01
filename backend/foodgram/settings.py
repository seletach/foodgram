import os

from dotenv import find_dotenv, load_dotenv
from pathlib import Path

load_dotenv(find_dotenv())

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'SECRET_KEY')

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split()

# Application definition

LOGGING = {
    'version': 1,

    'disable_existing_loggers': False,

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
        },

        'file': {
            'class': 'logging.FileHandler',
            'filename': 'api/all.log',
            'level': 'DEBUG',
            'mode': 'w',
            'encoding': 'utf-8',
        },
    },

    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO'
        },
    },
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework.authtoken',
    'djoser',
    'django_filters',
    'debug_toolbar',

    'api.apps.ApiConfig',
    'recipes.apps.RecipesConfig',
    'users.apps.UsersConfig'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = [
    '127.0.0.1',
]

ROOT_URLCONF = 'foodgram.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'foodgram.wsgi.application'


# Rest Framework

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ]
}

# Djoser

DJOSER = {
    'HIDE_USERS': False,
    'LOGIN_FIELD': 'email',
    'SERIALIZERS': {
        'user_create': 'djoser.serializers.UserCreateSerializer',
        'current_user': 'api.serializers.UserSerializer',
        'user': 'api.serializers.UserSerializer'
    },
    'PERMISSIONS': {
        'user_list': ['rest_framework.permissions.AllowAny'],
        'user': ['rest_framework.permissions.IsAuthenticatedOrReadOnly']
    },
}

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

if DEBUG:
    ENGINE_DATABASE = 'sqlite3'
else:
    ENGINE_DATABASE = 'postgresql'

DATABASES = {
    'default': {
        'ENGINE': f'django.db.backends.{ENGINE_DATABASE}',
        'NAME': os.getenv('POSTGRES_DB', 'django'),
        'USER': os.getenv('POSTGRES_USER', 'django'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', 5432)
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'ru-RU'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'collected_static'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

DOMAIN = os.getenv('DOMAIN')

CSRF_TRUSTED_ORIGINS = (f'https://{DOMAIN}',
                        f'http://{DOMAIN}')
