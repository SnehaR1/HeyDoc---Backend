from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=12, null=False, blank=False)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "phone", "password"]

    def __str__(self):
        return self.username
