import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')
django.setup()

print("Django setup complete")

try:
    from core.models import Account
    print("Models imported successfully")
except Exception as e:
    print(f"Error importing models: {e}")

try:
    from core.views import dashboard
    print("Views imported successfully")
except Exception as e:
    print(f"Error importing views: {e}")
