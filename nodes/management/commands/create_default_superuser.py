import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password


class Command(BaseCommand):
    help = "Creates initial default superuser with credentials set in .env"

    def handle(self, *args, **options):
        user = User(
            id=1,
            username=os.getenv("DEFAULT_SUPERUSER_USERNAME"),
            first_name=os.getenv("DEFAULT_SUPERUSER_FIRSTNAME"),
            last_name=os.getenv("DEFAULT_SUPERUSER_LASTNAME"),
            email=os.getenv("DEFAULT_SUPERUSER_EMAIL"),
            password=make_password(os.getenv("DEFAULT_SUPERUSER_PASSWORD")),
            is_staff=True,
            is_active=True,
            is_superuser=True,
        )

        try:
            user.save()

            self.stdout.write(
                self.style.SUCCESS("Successfully created default superuser")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error creating default superuser with exception {e}, probably it was already created?"
                )
            )
