import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_ROOT = os.path.join(BASE_DIR, 'run_media')
MEDIA_URL  = '/media/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO', # Cambia a 'DEBUG' para ver aún más detalle si es necesario
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# Seguridad
SECRET_KEY = 'django-insecure-!b@sy58-!&gbjrr&j7&6a!uh0k35kte0+f1wfuoor#p7m_*q(t'
DEBUG = True 
ALLOWED_HOSTS = ['fork202501-proyecto-equipo3-production.up.railway.app']
CSRF_TRUSTED_ORIGINS = ['http://*', 'https://fork202501-proyecto-equipo3-production.up.railway.app']


# Google Service Account
GOOGLE_SERVICE_ACCOUNT_FILE = os.path.join(
    BASE_DIR, 'credentials', 'proyectoacreditacion-458222-6eef112921f9.json'
)
# Carpeta central de Drive
GOOGLE_DRIVE_PARENT_FOLDER_ID = '1WPqjYgnamz1ipb_8oXA-Lz1Yodalp7fj'
# Carpeta de los avatar de los usuarios
AVATARS_DRIVE_FOLDER_ID = '1G1Jjkt6znuzbqPe4TcsetnTOO2yivEcI'
# Carpeta para los documentos
GOOGLE_DRIVE_ATTACHGENERIC_FOLDER_ID = '1tz6m4pe1M7GGeHa5h5-1BrU_Sv-JgBf4'
# Drive API
GOOGLE_DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
# Docs API
GOOGLE_DOCS_SCOPES  = ['https://www.googleapis.com/auth/documents']
# Gmail API
GOOGLE_GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']
# Calendar API:
GOOGLE_CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
# Carpeta para los informes finales
GOOGLE_DRIVE_REPORTS_FOLDER_ID = '1NefV50klc_znek9o-4HRun-fQYICAJVl'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'whitenoise.runserver_nostatic',

    #Apps creadas:
    'projects', 

    #core (imagenes y css que se usan en mas de una app).
    'core',

    #login (login y registro de usuarios):
    'login',

    #home:
    'home',

    #reports:
    'reports',

    #Traits:
    'traitManager',
    'traitList',

    #Formularios y factores:
    'assignments',
    'factorManager',
    'factorList',
    'formularios',
    'attachGeneric',

    #Aspectos(?)
    'aspectManager',
    'aspectList',

    #Database:
    'database',

    #Create Event:
    'calendar_create_event',

    #Meeting:
    'meeting_List',

    #Strategic Analysis
    'strategicAnalysis'
]

STORAGES = {
    # ...
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.LoginRequiredMiddleware',      # <-- nueva línea
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'todo_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'todo_app.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ProjectDB',
        'USER': 'ProjectDB_owner',
        'PASSWORD': 'npg_2u5RljTtBXwi',
        'HOST': 'ep-royal-sunset-a5l16xiy-pooler.us-east-2.aws.neon.tech',
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

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

LANGUAGE_CODE = 'en-co'
TIME_ZONE     = 'America/Bogota'
USE_I18N      = True
USE_TZ        = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [ BASE_DIR / 'core' / 'static' ]
#STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'login.User'   # antes: 'database.User'

AUTHENTICATION_BACKENDS = [
    'login.backends.CedulaBackend',
    'django.contrib.auth.backends.ModelBackend',
]

EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_HOST_USER     = 'icesiacreditacion@gmail.com'
EMAIL_HOST_PASSWORD = 'gcrabaqtbaxfybws'
EMAIL_USE_TLS       = True
DEFAULT_FROM_EMAIL  = EMAIL_HOST_USER

LOGIN_URL = '/login/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_REDIRECT_URL = '/home/'
LOGIN_EXEMPT_URLS = [
    r'^register/?$',          # si tienes una vista de registro
    r'^password-reset/?$',   
    r'^login/?$',           # formulario de login
    r'^login/logout/?$',    # logout
    r'^login/register',     # registro
    r'^login/verify',       # verificación
    r'^password_reset',     # olvido contraseña
    r'^static/.*',
    r'^media/.*',
    r'^admin/.*',
    r'^login/password_reset',
    r'^login/reset/.*',
    r'^/attach/',
]

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
