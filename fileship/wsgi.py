"""
WSGI config for fileship project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.conf import settings
from whitenoise import WhiteNoise  # type: ignore


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fileship.settings")

wsgi_app = get_wsgi_application()
application = WhiteNoise(wsgi_app, root="/app/static", prefix=settings.STATIC_URL)
application.add_files("/app/media", prefix=settings.MEDIA_URL)
