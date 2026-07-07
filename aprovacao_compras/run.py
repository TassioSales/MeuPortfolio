import os
from waitress import serve

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

serve(
    application,
    host="0.0.0.0",
    port=8504,
    threads=8,
)
