import os
import re

settings_path = 'winter_arc/settings.py'
if not os.path.exists(settings_path):
    print('settings.py not found')
    exit(0)

with open(settings_path, 'r') as f:
    content = f.read()

# Add environ import
content = content.replace('from pathlib import Path', 'from pathlib import Path\nimport environ\nimport os')

# Initialize environ
environ_init = '''
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
'''
content = content.replace("BASE_DIR = Path(__file__).resolve().parent.parent", environ_init)

# Replace SECRET_KEY
content = re.sub(r"SECRET_KEY = '.*?'", "SECRET_KEY = env('DJANGO_SECRET_KEY', default='unsafe-secret-key')", content)

# Replace DEBUG
content = content.replace(
    "DEBUG = True",
    "DEBUG = env('DJANGO_DEBUG', default=False)"
)

# Replace ALLOWED_HOSTS
content = content.replace(
    "ALLOWED_HOSTS = []",
    "ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])"
)

# Add INSTALLED_APPS
apps_to_add = [
    "'rest_framework',",
    "'corsheaders',",
    "'core',",
    "'accounts',",
    "'arcs',",
    "'goals',",
    "'tasks',",
    "'habits',",
    "'journal',",
    "'study',",
    "'workouts',",
    "'analytics',",
    "'gamification',",
    "'notifications',",
    "'api',",
]
for app in reversed(apps_to_add):
    content = content.replace(
        "'django.contrib.staticfiles',",
        f"'django.contrib.staticfiles',\n    {app}"
    )

# Add Middleware
content = content.replace(
    "'django.middleware.security.SecurityMiddleware',",
    "'django.middleware.security.SecurityMiddleware',\n    'corsheaders.middleware.CorsMiddleware',"
)

# Change TEMPLATES DIRS
content = content.replace(
    "'DIRS': [],",
    "'DIRS': [BASE_DIR / 'templates'],"
)

# Replace DATABASES
db_config = '''DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://winter_user:winter_password@127.0.0.1:5432/winter_arc')
}
'''
content = re.sub(r'DATABASES = \{.*?\}', db_config, content, flags=re.DOTALL)

# Add STATIC, MEDIA, CORS, DRF, CELERY settings at the end
additional_settings = '''
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

CORS_ALLOW_ALL_ORIGINS = True # For development only

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# Celery Configuration
CELERY_BROKER_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

AUTH_USER_MODEL = 'accounts.CustomUser'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'
'''
content += additional_settings

with open(settings_path, 'w') as f:
    f.write(content)
print('settings.py configured')
