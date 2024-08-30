from django.db import models
from shortuuid.django_fields import ShortUUIDField
from users.models import CustomUser


class Department(models.Model):
    dept_id = ShortUUIDField(
        unique=True,
        length=5,
        max_length=10,
        prefix="dept",
        alphabet="abcdefgh12345",
    )
    dept_name = models.CharField(max_length=50, unique=True, null=False, blank=False)
    dept_description = models.CharField(null=False, blank=False)
    dept_image = models.ImageField(upload_to="dept_images/", null=True, blank=True)


class CancelBooking(models.Model):
    CHOICES = [
        ("Patient Requested", "Patient Requested"),
        ("Doctor Not Available", "Doctor Not Available"),
        ("Other", "Other"),
    ]
    REFUND_CHOICES = [
        ("No Refund", "No Refund"),
        ("Refund Applicable", "Refund Applicable"),
        ("Refund Processing", "Refund Processing"),
        ("Refund Completed", "Refund Completed"),
    ]
    booking_id = models.IntegerField(null=False, blank=False, unique=True)
    reason = models.CharField(choices=CHOICES, blank=True, null=True)
    cancelled_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, blank=False, null=False
    )
    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.CASCADE, blank=False, null=False
    )
    refund = models.CharField(choices=REFUND_CHOICES, blank=True, null=True)
