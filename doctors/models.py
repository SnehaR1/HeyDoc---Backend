from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser
from adminapp.models import Department
from shortuuid.django_fields import ShortUUIDField
from datetime import time, timedelta, datetime, date
from users.models import CustomUser
from decimal import Decimal

# Create your models here.


class TimeSlot(models.Model):
    startTime = models.TimeField(unique=True, blank=False, null=False)
    endTime = models.TimeField(unique=True, blank=False, null=False)

    def generate_slot(self):
        slots = []
        time = self.startTime
        while time < self.endTime:
            slots.append(time)

            time = (datetime.combine(date.min, time) + timedelta(minutes=15)).time()
        return slots

    class Meta:
        abstract = True


class MorningSlot(TimeSlot):
    startTime = models.TimeField(default=time(9, 0))
    endTime = models.TimeField(default=time(13, 0))


class EveningSlot(TimeSlot):
    startTime = models.TimeField(default=time(14, 0))
    endTime = models.TimeField(default=time(18, 0))


class Doctor(AbstractBaseUser):
    doc_id = ShortUUIDField(
        unique=True,
        length=5,
        max_length=10,
        prefix="doc",
        alphabet="abcdefgh12345",
    )
    name = models.CharField(max_length=50, null=False, blank=False)
    email = models.EmailField(null=False, blank=False, unique=True)
    phone = models.CharField(null=False, blank=False)
    is_HOD = models.BooleanField(default=False)
    doc_image = models.ImageField(upload_to="doc_images/", null=True, blank=True)
    account_activated = models.BooleanField(default=False)
    description = models.CharField(null=True, blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        to_field="dept_id",
    )

    is_active = models.BooleanField(default=True)
    fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("200.00")
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "phone", "password", Department]

    def __str__(self):
        return self.email


class Availability(models.Model):
    DAY_CHOICES = [
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
        ("Sunday", "Sunday"),
    ]
    SLOT_CHOICES = [("Morning", "Morning"), ("Evening", "Evening")]
    slot = models.CharField(max_length=10, choices=SLOT_CHOICES, null=True, blank=True)
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    isAvailable = models.BooleanField(default=True)

    morning = models.ForeignKey(
        MorningSlot, on_delete=models.CASCADE, blank=True, null=True
    )
    evening = models.ForeignKey(
        EveningSlot, on_delete=models.CASCADE, blank=True, null=True
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        to_field="doc_id",
    )

    class Meta:
        unique_together = ("day_of_week", "doctor")


class Patient(models.Model):
    patient_id = ShortUUIDField(
        unique=True,
        length=5,
        max_length=10,
        prefix="pat",
        alphabet="abcdefgh12345",
    )
    gender = [("Female", "Female"), ("Male", "Male"), ("Other", "Other")]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    doctor = models.ManyToManyField(Doctor, blank=True)
    name = models.CharField(max_length=25, null=False, blank=False, unique=True)
    age = models.IntegerField(null=False, blank=False)
    gender = models.CharField(default="Male", choices=gender, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    weight = models.DecimalField(null=True, blank=True, decimal_places=2, max_digits=3)
    height = models.DecimalField(null=True, blank=True, decimal_places=2, max_digits=3)
    allergies = models.CharField(null=True, blank=True)
    symptoms = models.CharField(null=True, blank=True)
    diagnosis = models.CharField(null=True, blank=True)


class DoctorRequest(models.Model):
    email = models.EmailField(null=False, blank=False, unique=True)
    message = models.CharField(null=False, blank=False)


class BlackListedToken(models.Model):
    token = models.TextField()
    blacklisted_at = models.DateTimeField(auto_now_add=True)


class Booking(models.Model):
    PAYMENT_MODES = [("Direct", "Direct"), ("Razor Pay", "Razor Pay")]

    time_slot = models.TimeField()
    booked_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        to_field="name",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("completed", "Completed"),
        ],
        default="pending",
    )
    BOOKING_CHOICES = [("Booked", "Booked"), ("Cancelled", "Cancelled")]
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODES)
    booked_day = models.DateField(null=False, blank=False)
    date_of_booking = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, null=True, blank=True, to_field="doc_id"
    )
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    booking_status = models.CharField(choices=BOOKING_CHOICES, default="Booked")

    def __str__(self):
        return f"Booking for {self.patient} by {self.booked_by} on {self.booked_day}"

    class Meta:
        unique_together = ("booked_day", "patient", "doctor")
