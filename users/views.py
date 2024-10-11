from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CustomUser, OTP
from .serializer import (
    CustomUserSerializer,
    DoctorsViewSerializer,
    PatientFormSerializer,
)
from rest_framework import status
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from users.serializer import (
    CustomTokenObtainPairSerializer,
    BookingSerializer,
    BookingRecieptSerializer,
)
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
    Report,
    Notification,
)
from adminapp.serializer import DoctorSerializer, DepartmentSerializer
from doctors.serializer import AvailabilitySerializer, ReportSerializer
import pyotp
from django.core.cache import cache
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.utils import timezone
from adminapp.models import Department
from doctors.tasks import send_mail_task, send_sms_task
import os
from datetime import datetime
from collections import defaultdict
from rest_framework.permissions import IsAuthenticated


# Create your views here.
def index(request):
    return render(request, "build/index.html")


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

                return Response(
                    {"message": "Login successful", "data": response_data},
                    status=status.HTTP_200_OK,
                )

            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_class = IsAuthenticated

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            response = Response(
                {"message": "User successfully logged out"}, status=status.HTTP_200_OK
            )

            return response
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DoctorsView(APIView):
    permission_class = IsAuthenticated

    def get(self, request):
        try:

            doctors = Doctor.objects.select_related("department").filter(
                active=True, department__is_active=True, account_activated=True
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
    permission_class = IsAuthenticated

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
            booked_slots = Booking.objects.filter(booking_status="Booked").values(
                "booked_day", "time_slot"
            )

            slots = defaultdict(list)

            for booking in booked_slots:
                day = str(booking["booked_day"])
                slots[day].append(booking["time_slot"])

            slots = dict(slots)
            morning_slots = []
            evening_slots = []

            for avail in availability:
                if avail.slot == "Morning":
                    time_slot = "Morning Slots"
                    morning_slots = list(MorningSlot().generate_slot())

                elif avail.slot == "Evening":
                    time_slot = "Evening Slots"
                    evening_slots = list(EveningSlot().generate_slot())

            availability_serializer = AvailabilitySerializer(availability, many=True)
            days_available = Availability.objects.filter(
                doctor=doc_id, isAvailable=True
            ).values_list("day_of_week", flat=True)
            return Response(
                {
                    "message": "Availability data captured successfully",
                    "availability": availability_serializer.data,
                    "time_slot": time_slot,
                    "slots": slots,
                    "morning_slots": morning_slots,
                    "evening_slots": evening_slots,
                    "days_available": days_available,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PatientForm(APIView):
    permission_class = IsAuthenticated

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

    def put(self, request):
        try:
            patient_name = request.data.get("name")
            patient = get_object_or_404(Patient, name=patient_name)
            serializer = PatientFormSerializer(patient, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "Patient Info updated successfully!"},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CheckoutView(APIView):
    permission_class = IsAuthenticated

    def post(self, request):
        try:
            doc_id = request.data.get("doctor")

            payment_mode = request.data.get("payment_mode")
            payment_status = request.data.get("payment_status")
            booked_day = request.data.get("booked_day")
            time_slot = request.data.get("time_slot")
            consultation_mode = request.data.get("consultation_mode")
            booked_by = request.data.get("booked_by")

            print(doc_id)
            patient_name = request.data.get("patient")
            time = datetime.strptime(time_slot, "%H:%M:%S").time()
            if time.hour < 12:
                slot = "Morning"
            else:
                slot = "Evening"

            doctor = get_object_or_404(Doctor, doc_id=doc_id)

            serializer = BookingSerializer(data=request.data)
            if serializer.is_valid():

                serializer.validated_data["slot"] = slot
                serializer.validated_data["consultation_mode"] = consultation_mode
                serializer.save()
                if payment_status.lower() == "completed":
                    patient = get_object_or_404(Patient, name=patient_name)
                    if not patient.doctor.filter(id=doctor.id).exists():
                        patient.doctor.add(doctor.id)
                        print("doctor added")
                        patient.save()

                subject = "Doctor Apointment Done successfully"
                message = f"Dear {patient_name},Booking for Dr. {doctor.name} done successfully on {booked_day} at {time_slot}.Thank you for choosing us.Best Regards,Heydoc"
                email_from = os.getenv("EMAIL_HOST_USER")
                email_to = CustomUser.objects.get(id=booked_by).email
                send_mail_task.delay(subject, message, email_from, email_to)
                return Response(
                    {
                        "message": "Booking done successfully",
                        "data": serializer.data,
                        "doctor_name": doctor.name,
                        "payment_mode": payment_mode,
                        "payment_status": payment_status,
                        "consultation_mode": consultation_mode,
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
    permission_class = IsAuthenticated

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

                if booking.booked_day >= timezone.now().date():
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
                            "consultation_mode": booking.consultation_mode,
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
        Notification.objects.create(
            title="Someone Dropped Us A Message!",
            message=f"{email} has sent you a message!",
        )
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
    permission_class = IsAuthenticated

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
    permission_class = IsAuthenticated

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


class OTPVerification(APIView):
    def generate_otp(self):
        secret_key = pyotp.random_base32()
        totp = pyotp.TOTP(secret_key)
        otp = totp.now()
        return otp

    def post(self, request):

        email = request.data.get("email")
        phone = request.data.get("phone")
        if email == "" or phone == "":
            return Response(
                {"errors": "Please Provide Email or Phone Number!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if email:
                user = get_object_or_404(CustomUser, email=email)
                reciever = email

            elif phone:
                user = get_object_or_404(CustomUser, phone=phone)
                reciever = phone
            else:
                return Response(
                    {"errors": "Provide Registered Phone Number or Email!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if user:

                otp = self.generate_otp()

                if email:
                    OTP.objects.create(email=email, otp=otp)
                    email_from = os.getenv("EMAIL_HOST_USER")
                    send_mail_task(
                        "HeyDoc OTP for Password Reset",
                        f"Dear {user.username}\n Your Otp for password reset is {otp}.Please do not Share.\nBest Regards,HeyDoc",
                        email_from,
                        [email],
                    )

                if phone:
                    phone = "+91" + phone
                    OTP.objects.create(phone=phone, otp=otp)
                    send_sms_task(
                        phone,
                        f"Dear {user.username}\n Your Otp for password reset is {otp}.Please do not Share.\nBest Regards,HeyDoc",
                    )

                return Response(
                    {"message": f"OTP Successfully sent! Please Check"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": f"No user with the provided {reciever} exists!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    def post(self, request):
        email = request.data.get("email")
        phone = request.data.get("phone")
        otp = request.data.get("otp")

        if (not email and not phone) or not otp:
            return Response(
                {"error": "Email/Phone and OTP are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            if email:
                otp_record = OTP.objects.filter(email=email, otp=otp).latest(
                    "created_at"
                )
            elif phone:
                otp_record = OTP.objects.filter(phone=phone, otp=otp).latest(
                    "created_at"
                )
        except OTP.DoesNotExist:
            return Response(
                {"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST
            )
        if otp_record.is_valid():
            return Response(
                {"message": "OTP verified successfully"}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST
            )

    def patch(self, request):
        email = request.data.get("email")
        phone = request.data.get("phone")
        password = request.data.get("password")

        try:
            if email:
                user = CustomUser.objects.get(email=email)
            elif phone:
                user = CustomUser.objects.get(phone=phone)
            else:
                return Response(
                    {"error": "Something went wrong! please try again."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.password = make_password(password)
            user.save()
            return Response(
                {"message": "Password reset Successfully"}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReportsView(APIView):
    permission_class = IsAuthenticated

    def get(self, request):
        try:
            patient = request.query_params.get("name")
            reports = Report.objects.filter(patient__name=patient)
            if reports:
                serializer = ReportSerializer(reports, many=True)
                return Response(
                    {
                        "message": "Reports Retrieved Successfully",
                        "reports": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"message": "No reports to retreive", "reports": []},
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DepartmentsView(APIView):

    def get(self, request):
        try:
            departments = Department.objects.all()
            serializer = DepartmentSerializer(departments, many=True)
            doctors = Doctor.objects.all()
            doctor_serializer = DoctorSerializer(doctors, many=True)

            return Response(
                {
                    "message": "Departments retrieved",
                    "departments": serializer.data,
                    "doctors": doctor_serializer.data,
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class Reciepts(APIView):
    permission_class = IsAuthenticated

    def get(self, request):
        try:
            user_id = request.query_params.get("user_id")
            reciepts = Booking.objects.filter(
                booked_by=user_id, payment_status="completed", booking_status="Booked"
            )
            serializer = BookingRecieptSerializer(reciepts, many=True)
            return Response(
                {
                    "message": "Reciepts retrieved",
                    "reciepts": serializer.data,
                }
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
