import os
import django
from django.urls import reverse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')
django.setup()

try:
    url = reverse('search_ticker')
    print(f"SUCCESS: {url}")
except Exception as e:
    print(f"ERROR: {e}")
