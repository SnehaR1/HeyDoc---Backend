from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Create your models here.


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=12, null=False, blank=False, unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "phone", "password"]

    def __str__(self):
        return self.username


class OTP(models.Model):
    email = models.EmailField()
    phone = models.CharField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(default=timezone.now)

    def is_valid(self):
        expiration_time = timezone.now() - timezone.timedelta(minutes=5)
        return self.created_at >= expiration_time
