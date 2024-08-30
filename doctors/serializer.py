from rest_framework import serializers
from .models import DoctorRequest, Doctor, Availability
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from .utils import create_access_token, create_refresh_token


class DoctorRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorRequest
        fields = "__all__"


class DoctorLoginserializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        credentials = {"email": attrs.get("email"), "password": attrs.get("password")}
        print(attrs)
        doctor = Doctor.objects.filter(email=credentials["email"]).first()
        print(credentials["email"])
        if not doctor:
            raise serializers.ValidationError("Invalid Email")
        if not check_password(credentials["password"], doctor.password):
            raise serializers.ValidationError("Invalid password.")

        if not doctor.is_active:
            raise PermissionDenied(
                "Your account is blocked. Please contact the our team for more details"
            )
        if not doctor.account_activated:
            raise PermissionDenied(
                "Your account is not activated yet. Please send a request to the admin!"
            )

        refresh = create_refresh_token(doctor.doc_id)
        access = create_access_token(doctor.doc_id)
        data = {
            "refresh": str(refresh),
            "access": str(access),
            "user": {
                "doc_id": doctor.doc_id,
                "name": doctor.name,
                "email": doctor.email,
                "phone": doctor.phone,
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
        fields = ["slot", "day_of_week", "isAvailable"]
