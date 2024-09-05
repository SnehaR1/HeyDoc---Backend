from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CustomUser
from .serializer import (
    CustomUserSerializer,
    DoctorsViewSerializer,
    PatientFormSerializer,
)
from rest_framework import status
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from users.serializer import CustomTokenObtainPairSerializer, BookingSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from doctors.models import (
    Doctor,
    Availability,
    MorningSlot,
    EveningSlot,
    Patient,
    Booking,
)
from adminapp.serializer import DoctorSerializer
from doctors.serializer import AvailabilitySerializer

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.utils import timezone
from adminapp.models import Department
from doctors.tasks import send_mail_task
import os

# Create your views here.


class Register(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        if CustomUser.objects.filter(email=email).exists():
            return Response(
                {"error": "Account with this Email Already Exists!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(password)

        except ValidationError as e:
            return render({"errors": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        try:

            serializer = CustomUserSerializer(data=request.data)
            if serializer.is_valid():
                hashed_password = make_password(password)
                serializer.validated_data["password"] = hashed_password
                serializer.save()
                return Response(
                    {"message": "Account Created Successfully"},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        try:
            if serializer.is_valid(raise_exception=True):
                response_data = serializer.validated_data

                response = Response(
                    {"message": "Login successful", "data": response_data["user"]},
                    status=status.HTTP_200_OK,
                )

                response.set_cookie(
                    key="access_token",
                    value=response_data["access"],
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                )
                response.set_cookie(
                    key="refresh_token",
                    value=response_data["refresh"],
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                )

                return response
            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            response = Response(
                {"message": "User successfully logged out"}, status=status.HTTP_200_OK
            )
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DoctorsView(APIView):
    def get(self, request):
        try:

            doctors = Doctor.objects.select_related("department").filter(
                is_active=True, department__is_active=True
            )
            serializer = DoctorsViewSerializer(doctors, many=True)
            departments = Department.objects.all().values_list("dept_name", flat=True)

            return Response(
                {
                    "message": "Doctors Information Successfully retrieved!",
                    "doctors": serializer.data,
                    "departments": departments,
                },
                status=status.HTTP_200_OK,
            )

        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BookingView(APIView):
    def get(self, request):
        doc_id = request.query_params.get("doc_id")
        print(f"doc_id :{doc_id}")
        try:

            if not doc_id:
                return Response(
                    {"error": "Doctor ID is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            availability = Availability.objects.filter(doctor_id=doc_id)

            slots = []
            all_slots = []
            time_slot = "Not Available"
            booked_slots = Booking.objects.all().values_list("time_slot", flat=True)
            for avail in availability:
                if avail.slot == "Morning":
                    time_slot = "Morning Slots"
                    all_slots = MorningSlot().generate_slot()

                elif avail.slot == "Evening":
                    time_slot = "Evening Slots"
                    all_slots = EveningSlot().generate_slot()

            slots = [slot for slot in all_slots if slot not in booked_slots]
            availability_serializer = AvailabilitySerializer(availability, many=True)
            return Response(
                {
                    "message": "Availability data captured successfully",
                    "availability": availability_serializer.data,
                    "time_slot": time_slot,
                    "slots": slots,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PatientForm(APIView):
    def get(self, request):
        user = request.query_params.get("user_id")
        try:
            patients = Patient.objects.filter(user=user).values_list("name", flat=True)

            if Patient.objects.filter(user=user).exists():
                return Response(
                    {
                        "message": "Patient information from this account retrieved successfully!",
                        "patients": patients,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "message": "No patient registered from this account",
                        "patients": patients,
                    }
                )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            serializer = PatientFormSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "Patient Info saved successfully!"},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CheckoutView(APIView):
    def post(self, request):
        try:
            doc_id = request.data.get("doctor")
            payment_mode = request.data.get("payment_mode")
            payment_status = request.data.get("payment_status")
            booked_day = request.data.get("booked_day")
            time_slot = request.data.get("time_slot")
            booked_by = request.data.get("booked_by")
            print(doc_id)
            patient_name = request.data.get("patient")
            patient = get_object_or_404(Patient, name=patient_name)
            doctor = Doctor.objects.filter(doc_id=doc_id).first()
            patient.doctor.add(doctor)
            serializer = BookingSerializer(data=request.data)
            if serializer.is_valid():

                serializer.save()

                patient.save()
                subject = "Doctor Apointment Done successfully"
                message = f"Booking for Dr. {doctor.name} done successfully on {booked_day} at {time_slot}.Thank you for choosing us."
                email_from = os.getenv("EMAIL_HOST_USER")
                email_to = CustomUser.objects.get(id=booked_by).values_list(
                    "email", flat=True
                )
                send_mail_task.delay(subject, message, email_from, email_to)
                return Response(
                    {
                        "message": "Booking done successfully",
                        "data": serializer.data,
                        "doctor_name": doctor.name,
                        "payment_mode": payment_mode,
                        "payment_status": payment_status,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AppointmentsListView(APIView):
    def get(self, request):
        try:
            user_id = request.query_params.get("user")
            if not user_id:
                return Response(
                    {"error": "User parameter is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            bookings = Booking.objects.filter(booked_by_id=user_id)
            if not bookings.exists():
                return Response(
                    {"error": "No bookings found for this user"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            booking_data = []

            for booking in bookings:

                doctor_info = None

                if booking.booked_day > timezone.now().date():
                    doctor = booking.doctor
                    if doctor:
                        doctor_info = {
                            "doc_name": doctor.name,
                            "department": doctor.department.dept_name,
                        }

                    booking_data.append(
                        {
                            "id": booking.id,
                            "time_slot": booking.time_slot,
                            "booked_day": booking.booked_day,
                            "patient": booking.patient.name,
                            "doctor_info": doctor_info,
                            "amount": booking.amount,
                            "payment_status": booking.payment_status,
                            "booking_status": booking.booking_status,
                        }
                    )

            return Response(
                {
                    "message": "Appointments retrieved successfully!",
                    "data": booking_data,
                },
                status=status.HTTP_200_OK,
            )
        except Booking.DoesNotExist:
            return Response(
                {"error": "No bookings found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContactUsView(APIView):
    def post(self, request):
        email = request.data.get("email")
        subject = request.data.get("subject")
        message = request.data.get("message")
        admins = list(
            CustomUser.objects.filter(is_staff=True).values_list("email", flat=True)
        )
        email_from = os.getenv("EMAIL_HOST_USER")
        try:
            send_mail_task.delay(subject, message, email_from, admins)
            return Response(
                {"message": "Email sent successfully"}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    def get(self, request):
        user = request.query_params.get("user")

        try:

            patients = list(
                Patient.objects.prefetch_related("doctor").filter(user_id=user)
            )

            serializer = PatientFormSerializer(patients, many=True)

            return Response(
                {
                    "message": "Registered patients retrieved!",
                    "patients": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EditUser(APIView):
    def put(self, request):
        id = request.query_params.get("user_id")
        email = request.data.get("email")
        if CustomUser.objects.filter(email=email).exclude(id=id).exists():
            return Response(
                {"error": "User with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = get_object_or_404(CustomUser, id=id)
            serializer = CustomUserSerializer(user, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "User Updated Successfully!"}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
