from .models import (
    DoctorRequest,
    Doctor,
    BlackListedToken,
    Availability,
    MorningSlot,
    EveningSlot,
)
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .tasks import send_mail_task
from django.conf import settings
from users.models import CustomUser
from doctors.serializer import (
    DoctorRequestSerializer,
    DoctorLoginserializer,
    AvailabilitySerializer,
)
import os
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth.hashers import make_password
from users.models import OTP
from .tasks import send_mail_task, send_sms_task
from django.shortcuts import get_object_or_404
import pyotp

# Create your views here.


class DoctorRequestView(APIView):
    def get(self, request):
        try:
            doctor_requests = DoctorRequest.objects.all()
            serializer = DoctorRequestSerializer(doctor_requests, many=True)
            return Response(
                {
                    "message": "Doctor requests fetched successfully!",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        email = request.data.get("email")
        req_message = request.data.get("message")

        doctor = Doctor.objects.filter(email=email).first()
        if DoctorRequest.objects.filter(email=email).exists():
            return Response(
                {"error": "Doctor Request with this email exists!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not Doctor.objects.filter(email=email).exists():
            return Response(
                {"error": "No Doctor with that Email is registered!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if doctor.account_activated:
            return Response(
                {"error": "Doctor Account already activated!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            serializer = DoctorRequestSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                subject = "Request To Activate Doctors Account"
                message = f"Hey Admin,\n Dr.{doctor.name} has requested for you to activate his/her account.\nDoctors Email : {email}\nMessage:{req_message} Kindly do what is neccessary!\nBest Regards,\n HeyDoc"
                email_from = os.getenv("EMAIL_HOST_USER")
                recipient_list = list(
                    CustomUser.objects.filter(is_staff=True).values_list(
                        "email", flat=True
                    )
                )
                send_mail_task.delay(subject, message, email_from, recipient_list)
                return Response(
                    {"message": "Request sent successfully."}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        doctor_req = DoctorRequest.objects.filter(id=id).first()
        doctor = Doctor.objects.filter(email=doctor_req.email).first()
        action = request.data.get("action")
        subject = "HeyDoc Doctor Account Activation"
        accept_msg = f"Hey Dr.{doctor.name},\nYour Account is Successfully activated!\nYour registred Email : {doctor.email} is your username and set the password via forget password option or contact the admin to get the password set by the team.Happy consulting.\nBest Regards,\nHeyDoc"
        reject_msg = f"Hey Dr.{doctor.name},\nYour Request for Account Activation was rejected by the admin.Please contact the HeyDoc Team for further details.\nBest Regards,\nHeyDoc"
        email_from = os.getenv("EMAIL_HOST_USER")
        recipient_list = [doctor.email]
        try:
            if action == "accept":
                doctor.is_active = True
                doctor.account_activated = True
                doctor.save()
                doctor_req.delete()
                send_mail_task(subject, accept_msg, email_from, recipient_list)
                return Response(
                    {"message": "Doctor's account activated successfully."},
                    status=status.HTTP_200_OK,
                )
            elif action == "reject":
                doctor_req.delete()
                send_mail_task(subject, reject_msg, email_from, recipient_list)
                return Response(
                    {
                        "message": "Email notification regarding request rejection was successfully sent"
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "Invalid Action"}, status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DoctorLoginView(APIView):
    def post(self, request):

        serializer = DoctorLoginserializer(data=request.data)
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


class DoctorLogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            if refresh_token:
                BlackListedToken.objects.create(token=refresh_token)

            response = Response(
                {"message": "User successfully logged out"}, status=status.HTTP_200_OK
            )
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ScheduleForm(APIView):
    def get(self, request):
        try:
            day_choices = dict(Availability.DAY_CHOICES)
            slot_choices = dict(Availability.SLOT_CHOICES)

            return Response(
                {
                    "message": "Choices retrieved successfully",
                    "day_choices": list(day_choices.items()),
                    "slot_choices": list(slot_choices.items()),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, doc_id):

        try:
            availability = Availability.objects.filter(doctor_id=doc_id)

            if availability.exists():
                serializer = AvailabilitySerializer(availability, many=True)

                return Response(
                    {
                        "message": "Avalabilty data retrieved successfully!",
                        "availability": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "message": "Availability data has not been provided!",
                        "availability": availability,
                    },
                    status=status.HTTP_200_OK,
                )
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class Schedule(APIView):
    def post(self, request, doc_id):

        try:
            print(request)
            isAvailable = request.data.get("isAvailable")
            print(isAvailable)

            serializer = AvailabilitySerializer(data=request.data)
            if serializer.is_valid():
                serializer.validated_data["doctor_id"] = doc_id
                if isAvailable == "false":
                    serializer.validated_data["isAvailable"] = False
                    serializer.validated_data["slot"] = None

                else:
                    serializer.validated_data["isAvailable"] = True

                serializer.save()
                return Response(
                    {
                        "message": "Schedule information was saved successfully!",
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
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
                doctor = get_object_or_404(Doctor, email=email)
                reciever = email

            elif phone:
                doctor = get_object_or_404(Doctor, phone=phone)
                reciever = phone
            else:
                return Response(
                    {"errors": "Provide Registered Phone Number or Email!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if doctor:

                otp = self.generate_otp()

                if email:
                    OTP.objects.create(email=email, otp=otp)
                    email_from = os.getenv("EMAIL_HOST_USER")
                    send_mail_task(
                        "HeyDoc OTP for Password Reset",
                        f"Dear {doctor.name}\n Your Otp for password reset is {otp}.Please do not Share.\nBest Regards,HeyDoc",
                        email_from,
                        [email],
                    )

                if phone:
                    phone = "+91" + phone
                    OTP.objects.create(phone=phone, otp=otp)
                    send_sms_task(
                        phone,
                        f"Dear {doctor.name}\n Your Otp for password reset is {otp}.Please do not Share.\nBest Regards,HeyDoc",
                    )

                return Response(
                    {"message": f"OTP Successfully sent! Please Check"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": f"No doctor with the provided {reciever} exists!"},
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
                user = Doctor.objects.get(email=email)
            elif phone:
                user = Doctor.objects.get(phone=phone)
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
