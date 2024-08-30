from django.urls import path
from adminapp.views import DepartmentView, DoctorView, CancelAppointmentView

urlpatterns = [
    path("department/", DepartmentView.as_view(), name="department"),
    path("doctor/", DoctorView.as_view(), name="doctor"),
    path(
        "cancel_appointment/",
        CancelAppointmentView.as_view(),
        name="cancel_appointment",
    ),
]
