from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
import random
from core.communication import send_email


class FileshipUser(models.Model):
    user: User = models.OneToOneField("auth.User", on_delete=models.CASCADE)
    otp = models.CharField(null=True, blank=True, max_length=6)
    otp_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_from_email(cls, email: str):
        user, _ = User.objects.get_or_create(
            email=email,
            username=email,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        fuser, _ = FileshipUser.objects.get_or_create(
            user=user,
        )

        return fuser

    def send_otp(self):
        self.otp = "".join([str(random.randint(0, 9)) for _ in range(6)])

        send_email(
            to=self.user.email,
            body=f"<p>Your OTP code is <strong>{self.otp}</strong></p>",
        )

        self.otp_at = datetime.now()
        self.save()

    def clear_otp(self):
        self.otp = None
        self.otp_at = None
        self.save()

    def representation(self):
        return {
            "id": self.id,
            "email": self.user.email,
            "firstName": self.user.first_name,
            "lastName": self.user.last_name,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    def __str__(self):
        return self.user.__str__()
