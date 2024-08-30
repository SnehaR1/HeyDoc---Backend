from django.urls import path
from .views import (
    DoctorRequestView,
    DoctorLoginView,
    DoctorLogoutView,
    ScheduleForm,
    Schedule,
)

urlpatterns = [
    path("doctor_request/", DoctorRequestView.as_view(), name="doctor_request"),
    path("doctor_request/<int:id>", DoctorRequestView.as_view(), name="edit_request"),
    path("login/", DoctorLoginView.as_view(), name="doctor_login"),
    path("logout/", DoctorLogoutView.as_view(), name="doctor_logout"),
    path("scheduleform/", ScheduleForm.as_view(), name="scheduleform"),
    path("scheduleform/<str:doc_id>", ScheduleForm.as_view(), name="scheduleform"),
    path("schedule/", Schedule.as_view(), name="schedule"),
    path("schedule/<str:doc_id>", Schedule.as_view(), name="schedule"),
]
