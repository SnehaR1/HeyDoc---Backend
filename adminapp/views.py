from django.shortcuts import render
from .models import Department
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializer import DepartmentSerializer
from rest_framework import status
from .serializer import (
    DoctorSerializer,
    BlogsSerializer,
    AdminBookingSerializer,
    CancelBookingSerializer,
    NotificationSerializer,
)
from rest_framework.views import APIView
from django.contrib.auth.hashers import make_password
from doctors.models import Doctor, Booking, Notification
from django.shortcuts import get_object_or_404
from .models import CancelBooking, BlogAdditionalImage, Blogs
from django.utils import timezone
from users.models import CustomUser
from users.serializer import CustomUserSerializer
import os
from doctors.tasks import send_mail_task
from doctors.models import Patient
from django.db.models import Sum, Count
from django.utils.timezone import now
from django.db.models.functions import TruncMonth, TruncYear
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

# Create your views here.


class DepartmentView(APIView):
    permission_class = IsAuthenticated
    serializer_class = DepartmentSerializer

    def get(self, request):
        try:
            departments = Department.objects.all()
            serializer = self.serializer_class(departments, many=True)
            return Response(
                {
                    "message": "Successfully fetched department informations!",
                    "departments": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        try:
            dept_id = request.data.get("dept_id")
            is_active = request.data.get("is_active")
            department = get_object_or_404(Department, dept_id=dept_id)
            department.is_active = is_active
            department.save()
            if is_active:
                message = "Department is Unblocked!"
            else:
                message = "Department is Blocked"
            return Response(
                {
                    "message": message,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        dept_name = request.data.get("dept_name")
        if Department.objects.filter(dept_name=dept_name).exists():
            return Response(
                {"error": "Department with this name already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.serializer_class(data=request.data)

        try:
            if serializer.is_valid(raise_exception=True):
                serializer.validated_data["is_active"] = True
                serializer.save()
                return Response(
                    {"message": "Department added Successfully"},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, dept_id):
        try:

            department = get_object_or_404(Department, dept_id=dept_id)
            serializer = DepartmentSerializer(
                department, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "Department updated Successfully"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": serializer.errors},
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DoctorFormView(APIView):
    permission_class = IsAuthenticated
    serializer_class = DoctorSerializer

    def get(self, request):
        param = request.query_params.get("type", None)
        if param == "department":
            try:
                departments = list(
                    Department.objects.values("id", "dept_id", "dept_name")
                )

                return Response(
                    {
                        "message": "Departments info fetched successfully",
                        "data": departments,
                    },
                    status=status.HTTP_200_OK,
                )

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"error": "Invalid type parameter"}, status=status.HTTP_400_BAD_REQUEST
            )

    def post(self, request):
        doc_email = request.data.get("doc_email")
        dept_id = request.data.get("department")

        try:
            department = Department.objects.get(dept_id=dept_id)
        except Department.DoesNotExist:
            return Response(
                {"error": "Department does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        password = request.data.get("password")

        if Doctor.objects.filter(doc_email=doc_email).exists():
            return Response(
                {"message": "Doctor's Account with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            request.data["department"] = department.id
            request.data["is_doctor"] = True
            request.data["is_active"] = True
            request.data["active"] = True

            serializer = self.serializer_class(data=request.data)
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

    def put(self, request, doc_id):
        try:

            dept_name = request.data.get("department")

            doctor = get_object_or_404(Doctor, doc_id=doc_id)

            department = get_object_or_404(Department, dept_name=dept_name)

            mutable_data = request.data.copy()
            mutable_data["department"] = department.id

            serializer = self.serializer_class(doctor, data=mutable_data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "Doctor Information Updated Successfully!"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            print(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CancelAppointmentView(APIView):
    permission_class = IsAuthenticated

    def post(self, request):
        try:
            id = request.data.get("id")
            user_id = request.data.get("cancelled_by")
            user = get_object_or_404(CustomUser, id=user_id)
            booking = get_object_or_404(Booking, id=id)
            patient_name = request.data.get("patient")
            patient = get_object_or_404(Patient, name=patient_name)

            doctor_id = booking.doctor.doc_id
            doctor = Doctor.objects.get(doc_id=doctor_id)

            reason = request.data.get("reason")
            payment_status = booking.payment_status
            refund = ""
            if payment_status == "Pending" or payment_status == "pending":
                refund = "No Refund"
            else:
                refund = "Refund Applicable"
            if booking.booked_day > timezone.now().date():

                CancelBooking.objects.update_or_create(
                    booking_id=id,
                    reason=reason,
                    cancelled_by=user,
                    doctor=doctor,
                    refund=refund,
                    patient=patient,
                )

                bookings = Booking.objects.filter(
                    patient=patient_name, payment_status="completed", doctor=doctor_id
                )

                if bookings.count() == 1:
                    patient.doctor.remove(doctor.id)
                    patient.save()
                booking.booking_status = "cancelled"
                booking.save()
                subject = "Booking Cancelled sucessfully!"

                email_from = os.getenv("EMAIL_HOST_USER")
                recipient_list = list(user.email)

                if refund == "Refund Applicable":
                    Notification.objects.create(
                        title=f"{user.username} Cancelled Appointment",
                        message=f"Refund Applicable!",
                    )
                    message = "Your appointment has been successfully cancelled. The refund process is underway. Thank you for your patience."
                    email_message = f"Hey {user.username},\n Your Appointment with Dr.{doctor.name} has been cancelled.The refund process is underway. Thank you for your patience."
                else:
                    message = "Appointment has been cancelled successfully!"
                    email_message = f"Hey {user.username},\n Your Appointment with Dr.{doctor.name} has been cancelled."
                send_mail_task.delay(subject, email_message, email_from, recipient_list)
                return Response(
                    {"message": message},
                    status=status.HTTP_200_OK,
                )

            else:
                return Response(
                    {
                        "error": "You can no longer cancel or refund as the day has already passed"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        try:
            booking_id = request.query_params.get("booking_id")
            booking = CancelBooking.objects.get(booking_id=booking_id)
            serializer = CancelBookingSerializer(booking)
            doctor = booking.doctor.name

            cancelled_by = booking.cancelled_by.username

            return Response(
                {
                    "message": "Cancel Information Retrieved Successfully!",
                    "cancel_info": serializer.data,
                    "doctor": doctor,
                    "cancelled_by": cancelled_by,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        booking_id = request.data.get("booking_id")

        refund = request.data.get("refund")

        try:
            booking = CancelBooking.objects.get(booking_id=booking_id)
            user = booking.cancelled_by.username
            booking.refund = refund
            booking.save()
            if refund == "Refund Processing":
                message = f"Dear {user},\nYour Refund for the cancelled appointment with Dr. {booking.doctor.name} is being processed.Bear with us.You willl hear from us shortly.\nBest Regards,Heydoc"
            elif refund == "Refund Completed":
                message = f"Dear {user},\nYour Refund for the cancelled appointment with Dr. {booking.doctor.name} is done successfully!.If faced with any issues feel free to reach us.\nBest Regards,Heydoc"
            else:
                message = f"Dear {user},\nYour Refund Status for the cancelled appointment with Dr. {booking.doctor.name}Refund Status : {refund}.If faced with any issue feel free to contact us.\nBest Regards,Heydoc"
            subject = "Refund for cancelled Doctor Appointment"
            email_to = [booking.cancelled_by.email]
            print(email_to)
            email_from = os.getenv("EMAIL_HOST_USER")
            send_mail_task(subject, message, email_from, email_to)
            return Response(
                {
                    "message": "Refund Status Updated Successfully",
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DoctorView(APIView):
    permission_class = IsAuthenticated

    def get(self, request):
        try:
            doctors = Doctor.objects.all()
            serializer = DoctorSerializer(doctors, many=True)
            return Response(
                {
                    "message": "Doctor Informations retrieved successfully!",
                    "doctors": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        try:
            doc_id = request.data.get("doc_id")
            is_active = request.data.get("is_active")
            doctor = get_object_or_404(Doctor, doc_id=doc_id)
            doctor.active = is_active
            doctor.save()
            if is_active:
                message = "Unblocked the doctor successfully!"
            else:
                message = "Blocked the doctor successfully!"

            return Response(
                {
                    "message": message,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UsersView(APIView):
    permission_class = IsAuthenticated

    def get(self, request):
        try:
            users = CustomUser.objects.exclude(
                Q(email__isnull=True)
                | Q(email="")
                | Q(phone__isnull=True)
                | Q(phone="")
                | Q(username__isnull=True)
                | Q(username="")
            )
            serializer = CustomUserSerializer(users, many=True)
            return Response(
                {
                    "message": "User Informations retrieved successfully!",
                    "users": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        id = request.data.get("id")
        block = request.data.get("block")
        try:
            user = get_object_or_404(CustomUser, id=id)
            user.is_active = block
            user.save()
            if block:
                message = "User successfully blocked!"
            else:
                message = "User successfully unblocked!"
            return Response(
                {
                    "message": message,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BlogView(APIView):
    permission_class = IsAuthenticated

    def post(self, request):
        additional_images = request.FILES.getlist("add_images")
        try:
            serializer = BlogsSerializer(data=request.data)
            if serializer.is_valid():
                blog = serializer.save()

            if additional_images:
                for img in additional_images:
                    BlogAdditionalImage.objects.create(blog=blog, add_images=img)

                return Response(
                    {"message": "Blog added Successfully"},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id):
        try:
            additional_images = request.FILES.getlist("add_images")
            main_image = request.FILES.get("image")

            blog = get_object_or_404(Blogs, id=id)

            serializer = BlogsSerializer(instance=blog, data=request.data, partial=True)
            if serializer.is_valid():
                blog = serializer.save()

                if main_image:
                    blog.image = main_image
                    blog.save()

                if additional_images:
                    blog_Images = BlogAdditionalImage.objects.filter(blog_id=id)
                    blog_Images.delete()
                    for img in additional_images:
                        BlogAdditionalImage.objects.update_or_create(
                            blog=blog, add_images=img
                        )

                return Response(
                    {"message": "Blog updated successfully"}, status=status.HTTP_200_OK
                )

            return Response(
                {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        try:
            blogs = Blogs.objects.all()
            serializer = BlogsSerializer(blogs, many=True)
            return Response(
                {"Message": "Blogs retreived Successfully", "blogs": serializer.data}
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BookingsListView(APIView):
    permission_class = IsAuthenticated

    def get(self, request):
        try:
            bookings = (
                Booking.objects.select_related("doctor")
                .all()
                .order_by("-date_of_booking")
            )

            serializer = AdminBookingSerializer(bookings, many=True)

            return Response(
                {
                    "Message": "Bookings Information retreived Successfully",
                    "bookings": serializer.data,
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DashBoardView(APIView):
    permission_class = IsAuthenticated

    def get(self, request):
        try:
            notifications_objs = Notification.objects.filter(is_seen=False).order_by(
                "created_at"
            )[:5]
            notifications = NotificationSerializer(notifications_objs, many=True)
            total_earning = Booking.objects.filter(booking_status="Booked").aggregate(
                total=Sum("amount")
            )
            total_appointments = Booking.objects.filter(booking_status="Booked").count()
            doctors_count = Doctor.objects.filter(is_active=True).count()
            users_count = CustomUser.objects.filter(is_active=True).count()
            total_yearly = (
                Booking.objects.filter(booking_status="Booked")
                .annotate(year=TruncYear("booked_day"))
                .values("year")
                .annotate(total=Sum("amount"))
                .order_by("year")
            )
            total_monthly = (
                Booking.objects.filter(
                    booking_status="Booked", booked_day__year=now().year
                )
                .annotate(month=TruncMonth("booked_day"))
                .values("month")
                .annotate(total=Sum("amount"))
                .order_by("month")
            )
            online_consultations_earning = Booking.objects.filter(
                consultation_mode="Online"
            ).aggregate(total=Sum("amount"))
            offline_consultations_earning = Booking.objects.filter(
                consultation_mode="Offline"
            ).aggregate(total=Sum("amount"))

            patients_count = Patient.objects.all().count()
            total_monthly_list = list(total_monthly)

            current_month_total = (
                total_monthly_list[-1]["total"] if len(total_monthly_list) > 0 else 0
            )
            previous_month_total = (
                total_monthly_list[-2]["total"] if len(total_monthly_list) > 1 else 0
            )
            monthly_difference = current_month_total - previous_month_total

            total_yearly_list = list(total_yearly)
            current_year_total = (
                total_yearly_list[-1]["total"] if len(total_yearly_list) > 0 else 0
            )
            previous_year_total = (
                total_yearly_list[-2]["total"] if len(total_yearly_list) > 1 else 0
            )
            yearly_difference = current_year_total - previous_year_total

            top_doctors = (
                Booking.objects.filter(booking_status="Booked")
                .values("doctor__name")
                .annotate(total_bookings=Count("doctor"))
                .order_by("-total_bookings")[:5]
            )

            return Response(
                {
                    "notifications": notifications.data,
                    "total_earning": total_earning,
                    "total_appointments": total_appointments,
                    "doctors_count": doctors_count,
                    "users_count": users_count,
                    "total_monthly": total_monthly,
                    "online_consultations": online_consultations_earning,
                    "offline_consultations": offline_consultations_earning,
                    "patients_count": patients_count,
                    "monthly_difference": monthly_difference,
                    "yearly_difference": yearly_difference,
                    "current_month_total": current_month_total,
                    "current_year": current_year_total,
                    "total_yearly": total_yearly,
                    "top_doctors": top_doctors,
                }
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, id):
        try:
            notification = get_object_or_404(Notification, id=id)
            notification.is_seen = True
            notification.save()
            return Response(
                {"message": "Notification Successfully updated"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
