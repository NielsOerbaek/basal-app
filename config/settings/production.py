import os

import dj_database_url

from .base import *

DEBUG = False

SECRET_KEY = os.environ['SECRET_KEY']

DATABASES = {
    'default': dj_database_url.config(
        default='postgres://localhost/basal',
        conn_max_age=600,
    )
}

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'  # Required for Summernote editor in admin
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# CSRF trusted origins (required when behind reverse proxy)
CSRF_TRUSTED_ORIGINS = [
    f"https://{host.strip()}" for host in os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')
] + ['https://localhost', 'http://localhost']

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.example.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
