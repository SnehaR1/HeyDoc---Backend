from django.shortcuts import render
from .models import Department
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializer import DepartmentSerializer
from rest_framework import status
from .serializer import DoctorSerializer
from rest_framework.views import APIView
from django.contrib.auth.hashers import make_password
from doctors.models import Doctor, Booking
from django.shortcuts import get_object_or_404
from .models import CancelBooking
from django.utils import timezone

# Create your views here.


class DepartmentView(APIView):

    serializer_class = DepartmentSerializer

    def get(self):
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


class DoctorView(APIView):
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


class BookingListView(APIView):
    def get(self, request):
        pass


class CancelAppointmentView(APIView):
    def post(self, request):
        try:
            id = request.data.get("id")
            user = request.data.get("cancelled_by")
            booking = get_object_or_404(Booking, id=id)

            doctor = booking.doctor.name
            reason = request.data.get("reason")
            payment_status = booking.payment_status
            refund = ""
            if payment_status == "Pending" or payment_status == "pending":
                refund = "No Refund"
            else:
                refund = "Refund Requested"
            if booking.booked_day > timezone.now().date():

                cancel_booking = CancelBooking(
                    booking_id=id,
                    reason=reason,
                    cancelled_by=user,
                    doctor=doctor,
                    refund=refund,
                )
                cancel_booking.save()
                booking.booking_status = "Cancelled"
                booking.save()
            else:
                return Response(
                    {
                        "error": "You can no longer cancel or refund as the day has already passed"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
