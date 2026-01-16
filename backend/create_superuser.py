import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "social_media.settings")
django.setup()

User = get_user_model()
if not User.objects.filter(email="admin@beyou.com").exists():
    print(" Creating superuser...")
    User.objects.create_superuser(
        username=os.environ.get("ADMIN_NAME"),
        email = os.environ.get("ADMIN_EMAIL"),
        password = os.environ.get("ADMIN_PASSWORD"),

    )
    print("Superuser created.")
else:
    print("Superuser already exists.")
