from rest_framework import serializers
from .models import CustomUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.models import CustomUser
from django.contrib.auth import authenticate
from rest_framework.exceptions import PermissionDenied
from doctors.models import Doctor, Booking, Patient
from adminapp.serializer import DepartmentSerializer
from doctors.serializer import AvailabilitySerializer
from adminapp.models import Department


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = "__all__"

    def to_represntation(self, instance):
        representation = super().to_representation(instance)
        representation.pop("password", None)
        return representation


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = CustomUser.EMAIL_FIELD

    def validate(self, attrs):
        credentials = {"email": attrs.get("email"), "password": attrs.get("password")}

        user = authenticate(**credentials)
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise PermissionDenied(
                "Your account is blocked. Please contact the our team for more details"
            )
        refresh = self.get_token(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "is_staff": user.is_staff,
            },
        }

        return data


class DoctorsViewSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer()

    class Meta:
        model = Doctor
        fields = [
            "name",
            "description",
            "is_HOD",
            "doc_image",
            "department",
            "doc_id",
            "fee",
        ]


class DoctorRecieptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ["name"]


class BookingRecieptSerializer(serializers.ModelSerializer):
    razorpay_payment_id = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    doctor = DoctorRecieptSerializer()

    class Meta:
        model = Booking
        fields = [
            "booked_day",
            "payment_mode",
            "time_slot",
            "booked_by",
            "amount",
            "doctor",
            "patient",
            "razorpay_payment_id",
            "payment_status",
            "consultation_mode",
            "date_of_booking",
        ]


class BookingSerializer(serializers.ModelSerializer):
    razorpay_payment_id = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    class Meta:
        model = Booking
        fields = [
            "booked_day",
            "payment_mode",
            "time_slot",
            "booked_by",
            "amount",
            "doctor",
            "patient",
            "razorpay_payment_id",
            "payment_status",
            "consultation_mode",
            "date_of_booking",
        ]


class PatientFormSerializer(serializers.ModelSerializer):
    doctor = serializers.StringRelatedField(many=True, read_only=True)
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = Patient
        fields = ["name", "age", "gender", "phone", "user", "doctor", "is_active"]
