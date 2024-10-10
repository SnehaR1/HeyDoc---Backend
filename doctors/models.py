from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser
from adminapp.models import Department
from shortuuid.django_fields import ShortUUIDField
from datetime import time, timedelta, datetime, date
from users.models import CustomUser
from decimal import Decimal
from django.utils import timezone
from channels.layers import get_channel_layer

from asgiref.sync import async_to_sync

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


class Doctor(CustomUser):
    doc_email = models.EmailField(unique=True, blank=True, null=True)
    doc_phone = models.CharField(unique=True, blank=True, null=True)
    doc_id = ShortUUIDField(
        unique=True,
        length=5,
        max_length=10,
        prefix="doc",
        alphabet="abcdefgh12345",
    )

    name = models.CharField(max_length=50, null=False, blank=False)

    is_HOD = models.BooleanField(default=False)
    doc_image = models.ImageField(upload_to="doc_images/", null=True, blank=True)
    account_activated = models.BooleanField(default=False)
    description = models.CharField(null=True, blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, to_field="dept_id", related_name="doctors"
    )
    active = models.BooleanField(default=True)
    is_doctor = models.BooleanField(default=False)
    fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("200.00")
    )

    USERNAME_FIELD = "doc_email"
    REQUIRED_FIELDS = [
        "name",
        "doc_phone",
    ]

    def __str__(self):
        return self.doc_email


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
    online_consultation = models.BooleanField(default=False)

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
    doctor = models.ManyToManyField(Doctor, blank=True, related_name="doctor")
    name = models.CharField(max_length=25, null=False, blank=False, unique=True)
    age = models.IntegerField(null=False, blank=False)
    gender = models.CharField(default="Male", choices=gender, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("name", "user")


class DoctorRequest(models.Model):
    email = models.EmailField(null=False, blank=False, unique=True)
    message = models.CharField(null=False, blank=False)


class BlackListedToken(models.Model):
    token = models.TextField()
    blacklisted_at = models.DateTimeField(auto_now_add=True)


class Booking(models.Model):
    PAYMENT_MODES = [("Direct", "Direct"), ("Razor Pay", "Razor Pay")]
    SLOT_CHOICES = [("Morning", "Morning"), ("Evening", "Evening")]
    slot = models.CharField(choices=SLOT_CHOICES)
    time_slot = models.TimeField()
    booked_by = models.ForeignKey(
        CustomUser, related_name="custom_user", on_delete=models.CASCADE
    )
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
    CONSULTATION_CHOICES = [("Offline", "Offline"), ("Online", "Online")]
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODES)
    booked_day = models.DateField(null=False, blank=False)
    date_of_booking = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        to_field="doc_id",
    )
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    booking_status = models.CharField(choices=BOOKING_CHOICES, default="Booked")
    consultation_mode = models.CharField(
        choices=CONSULTATION_CHOICES, default="Offline"
    )

    def __str__(self):
        return f"Booking for {self.patient} by {self.booked_by} on {self.booked_day}"

    class Meta:
        unique_together = ("booked_day", "patient", "doctor", "booking_status")


class Report(models.Model):
    report_id = ShortUUIDField(
        unique=True,
        length=5,
        max_length=10,
        prefix="rep",
        alphabet="abcdefgh12345",
    )
    weight = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    height = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    allergies = models.TextField(null=True, blank=True, default="NA")
    symptoms = models.TextField(null=True, blank=True)
    diagnosis = models.TextField(null=True, blank=True, default="NA")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    report_date = models.DateField(auto_now_add=True)
    medications = models.TextField(null=True, blank=True, default="NA")
    family_history = models.TextField(null=True, blank=True, default="NA")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, default=1)

    class Meta:
        unique_together = ("report_date", "doctor", "patient")


class LeaveApplication(models.Model):
    LEAVE_TYPES = [
        ("Sick Leave", "Sick Leave"),
        ("Vacation Leave", "Vacation Leave"),
        ("Personal Leave", "Personal Leave"),
        ("Maternity Leave", "Maternity Leave"),
        ("Paternity Leave", "Paternity Leave"),
        ("Bereavement Leave", "Bereavement Leave"),
    ]
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, default=1)
    leave_type = models.CharField(
        null=False, blank=False, choices=LEAVE_TYPES, default="Sick Leave"
    )
    leave_start_date = models.DateField(null=False, blank=False)
    leave_end_date = models.DateField(null=False, blank=False)
    reason = models.TextField()
    supporting_document = models.FileField(
        upload_to="leave_documents/", null=True, blank=True
    )
    submission_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("doctor", "submission_date")


class Notification(models.Model):

    message = models.CharField(
        null=False,
        blank=False,
    )
    title = models.CharField(null=False, blank=False, default="Sick Leave")
    is_seen = models.BooleanField(default=False)

    created_at = models.DateField(auto_now_add=True)
