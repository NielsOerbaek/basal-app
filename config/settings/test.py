from .development import *  # noqa: F403

# Never send real emails during tests
RESEND_API_KEY = None
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
