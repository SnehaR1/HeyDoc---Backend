from django.shortcuts import render
from .models import Department
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializer import DepartmentSerializer
from rest_framework import status
from .serializer import DoctorSerializer, BlogsSerializer, AdminBookingSerializer
from rest_framework.views import APIView
from django.contrib.auth.hashers import make_password
from doctors.models import Doctor, Booking
from django.shortcuts import get_object_or_404
from .models import CancelBooking, BlogAdditionalImage, Blogs
from django.utils import timezone
from users.models import CustomUser
from users.serializer import CustomUserSerializer
import os
from doctors.tasks import send_mail_task

# Create your views here.


class DepartmentView(APIView):

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
    serializer_class = DoctorSerializer

    def get(self, request):
        param = request.query_params.get("type", None)
        if param == "department":
            try:
                departments = list(Department.objects.values("dept_id", "dept_name"))

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
        email = request.data.get("email")
        password = request.data.get("password")
        if Doctor.objects.filter(email=email).exists():
            return Response(
                {"message": "Doctor's Account with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
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
            doctor = get_object_or_404(Doctor, doc_id=doc_id)
            serializer = self.serializer_class(doctor, data=request.data, partial=True)
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
    def post(self, request):
        try:
            id = request.data.get("id")
            user_id = request.data.get("cancelled_by")
            user = get_object_or_404(CustomUser, id=user_id)
            booking = get_object_or_404(Booking, id=id)

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

                cancel_booking = CancelBooking.objects.update_or_create(
                    booking_id=id,
                    reason=reason,
                    cancelled_by=user,
                    doctor=doctor,
                    refund=refund,
                )

                booking.booking_status = "Cancelled"
                booking.save()
                subject = "Booking Cancelled sucessfully!"

                email_from = os.getenv("EMAIL_HOST_USER")
                recipient_list = list(user.email)

                if refund == "Refund Applicable":
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


class DoctorView(APIView):
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
            doctor.is_active = is_active
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
    def get(self, request):
        try:
            users = CustomUser.objects.all()
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
    def get(self, request):
        try:
            bookings = Booking.objects.all()
            serializer = AdminBookingSerializer(bookings, many=True)
            return Response(
                {
                    "Message": "Bookings Information retreived Successfully",
                    "bookings": serializer.data,
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
