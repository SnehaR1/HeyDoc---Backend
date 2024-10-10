from rest_framework import serializers
from .models import (
    DoctorRequest,
    Doctor,
    Availability,
    Patient,
    Booking,
    Report,
    LeaveApplication,
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
import jwt
from datetime import datetime, timedelta
from django.conf import settings


class DoctorRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorRequest
        fields = "__all__"


class DoctorLoginSerializer(serializers.Serializer):
    doc_email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        credentials = {
            "doc_email": attrs.get("doc_email"),
            "password": attrs.get("password"),
        }

        doctor = Doctor.objects.filter(doc_email=credentials["doc_email"]).first()
        if not doctor:
            raise serializers.ValidationError("Invalid Email")

        if not check_password(credentials["password"], doctor.password):
            raise serializers.ValidationError("Invalid password.")

        if not doctor.active:
            raise PermissionDenied(
                "Your account is blocked. Please contact our team for more details."
            )

        if not doctor.account_activated:
            raise PermissionDenied(
                "Your account is not activated yet. Please send a request to the admin!"
            )

        refresh = RefreshToken.for_user(doctor)

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "doc_id": doctor.doc_id,
                "name": doctor.name,
                "doc_email": doctor.doc_email,
                "doc_phone": doctor.doc_phone,
                "is_HOD": doctor.is_HOD,
                "department": doctor.department.dept_name,
                "doc_image": doctor.doc_image.url if doctor.doc_image else None,
            },
        }

        return data


class AvailabilitySerializer(serializers.ModelSerializer):
    slot = serializers.CharField(required=False, allow_null=True)
    day_of_week = serializers.CharField(required=False)
    isAvailable = serializers.BooleanField(required=False)

    class Meta:
        model = Availability
        fields = ["slot", "day_of_week", "isAvailable", "online_consultation"]


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = "__all__"


class BookingSerialzier(serializers.ModelSerializer):
    patient = PatientSerializer()

    class Meta:
        model = Booking
        fields = "__all__"


class DoctorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Doctor
        fields = "__all__"


# class ReportDoctorSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Doctor
#         fields = ["name"]


class ReportSerializer(serializers.ModelSerializer):
    doctor = serializers.PrimaryKeyRelatedField(queryset=Doctor.objects.all())

    class Meta:
        model = Report
        fields = "__all__"


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = "__all__"
