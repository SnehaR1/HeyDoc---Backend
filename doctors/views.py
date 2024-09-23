from .models import (
    DoctorRequest,
    Doctor,
    BlackListedToken,
    Availability,
    MorningSlot,
    EveningSlot,
    Booking,
    Patient,
    Report,
    LeaveApplication,
    Notification,
)
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .tasks import send_mail_task
from django.conf import settings
from users.models import CustomUser, OTP
from doctors.serializer import (
    DoctorRequestSerializer,
    DoctorLoginserializer,
    AvailabilitySerializer,
    DoctorSerializer,
)
import os
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth.hashers import make_password

from .tasks import send_mail_task, send_sms_task
from django.shortcuts import get_object_or_404
import pyotp
import calendar
from django.utils.timezone import now
from adminapp.models import CancelBooking
from .serializer import (
    PatientSerializer,
    BookingSerialzier,
    ReportSerializer,
    LeaveApplicationSerializer,
)
from datetime import datetime


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
                morning = MorningSlot()
                evening = EveningSlot()
                morning_slots = morning.generate_slot()
                evening_slots = evening.generate_slot()
                return Response(
                    {
                        "message": "Avalabilty data retrieved successfully!",
                        "availability": serializer.data,
                        "morning_slots": morning_slots,
                        "evening_slots": evening_slots,
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

    def patch(self, request, doc_id):

        day = request.data.get("day")
        print(f"day:{day}")

        slot = request.data.get("slot")
        online_consultation = request.data.get("online_consultation")
        print(slot)
        try:
            day_number = list(calendar.day_name).index(day)
            django_week_day_number = (day_number + 2) % 7 or 7
            today = now().date()
            bookings = None
            email_from = os.getenv("EMAIL_HOST_USER")
            online_present_status = Availability.objects.get(
                doctor_id=doc_id, day_of_week=day
            )

            if online_present_status.online_consultation != online_consultation:
                online_present_status.online_consultation = online_consultation
                online_present_status.save()
                if online_consultation == False:
                    bookings = Booking.objects.filter(
                        booked_day__week_day=django_week_day_number,
                        booked_day__gt=today,
                        consultation_mode="Online",
                    )
                    for booking in bookings:
                        booking.booking_status = "cancelled"
                        booking.save()
                        if booking.payment_status == "Completed":
                            CancelBooking.objects.create(
                                booking_id=booking.id,
                                cancelled_by=booking.booked_by,
                                doctor=booking.doctor,
                                reason="Doctor Not Available",
                                refund="Refund Applicable",
                            )
                        elif booking.payment_status == "Pending":
                            CancelBooking.objects.create(
                                booking_id=booking.id,
                                cancelled_by=booking.booked_by,
                                doctor=booking.doctor,
                                reason="Doctor Not Available",
                                refund="No Refund",
                            )
                    bookings_emails = Booking.objects.filter(
                        booked_day__week_day=django_week_day_number,
                        booked_day__gt=today,
                    ).values_list("booked_by__email", flat=True)
                    if bookings_emails:
                        subject = "Your Doctor Appointment Cancelled!"
                        message = f"Dear Sir/Ma'am,\n We are really sorry to inform you that as the doctor is not available for the booked day.Our Team will contact you shortly and if refund is applicable,you will be refunded ASAP.Sorry for the inconvenience cause.Do visit us again to book the next best available slot.\n Best Regards,\nHeyDoc"
                        email_from = os.getenv("EMAIL_HOST_USER")
                        send_mail_task(subject, message, email_from, bookings_emails)
                        return Response(
                            {
                                "message": "Availability updated!",
                            },
                            status=status.HTTP_200_OK,
                        )

            if slot != "Not Available":
                availability = Availability.objects.get(
                    doctor_id=doc_id, day_of_week=day
                )
                availability.slot = slot
                availability.save()

                if slot == "Morning":
                    bookings = Booking.objects.filter(
                        booked_day__week_day=django_week_day_number,
                        booked_day__gt=today,
                        slot="Evening",
                    )
                    bookings_emails = Booking.objects.filter(
                        booked_day__week_day=django_week_day_number,
                        booked_day__gt=today,
                        slot="Evening",
                    ).values_list("booked_by__email", flat=True)
                elif slot == "Evening":
                    bookings = Booking.objects.filter(
                        booked_day__week_day=django_week_day_number,
                        booked_day__gt=today,
                        slot="Morning",
                    )
                    bookings_emails = Booking.objects.filter(
                        booked_day__week_day=django_week_day_number,
                        booked_day__gt=today,
                        slot="Morning",
                    ).values_list("booked_by__email", flat=True)
                if bookings:
                    subject = "HeyDoc Doctor Appointment Slot Change"
                    if slot == "Morning":
                        message = f"Dear User,\n There has been a change in slot for doctor availability.Our Team will call you shortly.If you are not available for evening slot you can cancel the appointment via our website.Sorry for the inconvinience caused.Please do visit us again.\nBest Regards,\nHeyDoc"
                    else:
                        message = f"Dear User,\n There has been a change in slot for doctor availability.Our Team will call you shortly.If you are not available for morning slot you can cancel the appointment via our website.Sorry for the inconvinience caused.Please do visit us again.\nBest Regards,\nHeyDoc"
                    send_mail_task(subject, message, email_from, bookings_emails)
                return Response(
                    {
                        "message": "Availability updated!",
                    },
                    status=status.HTTP_200_OK,
                )
            elif slot == "Not Available":
                availability = Availability.objects.get(
                    doctor_id=doc_id, day_of_week=day
                )
                availability.isAvailable = False
                availability.save()

                bookings = Booking.objects.filter(
                    booked_day__week_day=django_week_day_number, booked_day__gt=today
                )
                for booking in bookings:
                    booking.booking_status = "cancelled"
                    booking.save()
                    if booking.payment_status == "Completed":
                        CancelBooking.objects.create(
                            booking_id=booking.id,
                            cancelled_by=booking.booked_by,
                            doctor=booking.doctor,
                            reason="Doctor Not Available",
                            refund="Refund Applicable",
                        )
                    elif booking.payment_status == "Pending":
                        CancelBooking.objects.create(
                            booking_id=booking.id,
                            cancelled_by=booking.booked_by,
                            doctor=booking.doctor,
                            reason="Doctor Not Available",
                            refund="No Refund",
                        )
                bookings_emails = Booking.objects.filter(
                    booked_day__week_day=django_week_day_number, booked_day__gt=today
                ).values_list("booked_by__email", flat=True)
                if bookings_emails:
                    subject = "Your Doctor Appointment Cancelled!"
                    message = f"Dear Sir/Ma'am,\n We are really sorry to inform you that as the doctor is not available for the booked day.Our Team will contact you shortly and if refund is applicable,you will be refunded ASAP.Sorry for the inconvenience cause.Do visit us again to book the next best available slot.\n Best Regards,\nHeyDoc"
                    email_from = os.getenv("EMAIL_HOST_USER")
                    send_mail_task(subject, message, email_from, bookings_emails)
                    return Response(
                        {
                            "message": "Availability updated!",
                        },
                        status=status.HTTP_200_OK,
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


class PatientsView(APIView):
    def get(self, request):
        try:
            doc_id = request.query_params.get("doc_id")

            doctor = Doctor.objects.get(doc_id=doc_id)

            patients = Patient.objects.filter(doctor=doctor.id)
            patients_data = []

            for patient in patients:

                latest_appointment = (
                    Booking.objects.filter(
                        patient=patient,
                        payment_status="completed",
                        booking_status="Booked",
                    )
                    .order_by("-booked_day")
                    .first()
                )

                last_appointment_date = (
                    latest_appointment.booked_day if latest_appointment else None
                )

                patient_data = PatientSerializer(patient).data
                patient_data["last_appointment"] = last_appointment_date

                patients_data.append(patient_data)

            return Response(
                {
                    "message": "Patient Information successfully retrieved!",
                    "patients": patients_data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DashboardView(APIView):
    def get(self, request):
        try:
            doc_id = request.query_params.get("doc_id")
            todays_appointments = Booking.objects.filter(
                payment_status="completed",
                booking_status="Booked",
                booked_day=datetime.now().date(),
                doctor=doc_id,
            )
            serializer = BookingSerialzier(todays_appointments, many=True)
            return Response(
                {
                    "message": "Today's appointments retreived successfully!",
                    "patients": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DoctorProfileView(APIView):
    def get(self, request):
        try:
            doc_id = request.query_params.get("doc_id")
            doctor = get_object_or_404(Doctor, doc_id=doc_id)

            return Response(
                {"message": "Doctor Profile Updated successfully!", "doctor": doctor},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, doc_id):
        try:
            doctor = Doctor.objects.get(doc_id=doc_id)

            serializer = DoctorSerializer(doctor, data=request.data, partial=True)
            print(request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "Doctor Profile Updated successfully!"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReportView(APIView):
    def get(self, request):
        user_id = request.query_params.get("user_id")
        patient_name = request.query_params.get("patient_name")
        patient_id = request.query_params.get("patient")

        if user_id and patient_name:

            try:
                patient = Patient.objects.get(user=user_id, name=patient_name)
                serializer = PatientSerializer(patient)
                return Response({"patient": serializer.data}, status=status.HTTP_200_OK)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        elif patient_id:
            try:
                reports = Report.objects.filter(patient=patient_id)
                patient = Patient.objects.get(id=patient_id)
                patient_serializer = PatientSerializer(patient)
                serializer = ReportSerializer(reports, many=True)
                return Response(
                    {
                        "message": "reports retreived successfully",
                        "reports": serializer.data,
                        "patient": patient_serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            user = request.data.get("user_id")
            patient_name = request.data.get("patient_name")
            doc_id = request.data.get("doctor")
            doctor = get_object_or_404(Doctor, doc_id=doc_id)
            patient_obj = get_object_or_404(Patient, user=user, name=patient_name)
            patient = patient_obj.id
            print(patient)
            request.data.pop("patient_name", None)
            request.data.pop("doctor", None)
            request.data["doctor"] = doctor.id
            request.data["patient"] = patient
            serializer = ReportSerializer(data=request.data)
            if serializer.is_valid():

                serializer.save(patient_id=patient)
                return Response(
                    {"message": "Report added successfully!"},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveApplicationView(APIView):
    def post(self, request):
        try:

            doc_id = request.data.get("doctor")
            leave_type = request.data.get("leave_type")

            doctor = get_object_or_404(Doctor, doc_id=doc_id)
            request.data.pop("doctor", None)
            request.data["doctor"] = doctor.id

            serializer = LeaveApplicationSerializer(data=request.data)
            if serializer.is_valid():
                Notification.objects.create(
                    title="Leave Application",
                    message=f"{doctor.name} has submitted Leave Application!",
                )

                serializer.save()

                return Response(
                    {"message": "Leave Application saved successfully!"},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
