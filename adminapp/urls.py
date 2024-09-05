from django.urls import path
from adminapp.views import (
    DepartmentView,
    DoctorFormView,
    CancelAppointmentView,
    DoctorView,
    UsersView,
    BlogView,
    BookingsListView,
)

urlpatterns = [
    path("department/", DepartmentView.as_view(), name="department"),
    path("department/<str:dept_id>/", DepartmentView.as_view(), name="edit_department"),
    path("doctor_form/", DoctorFormView.as_view(), name="doctor_form"),
    path("doctor_form/<str:doc_id>/", DoctorFormView.as_view(), name="edit_doctor"),
    path("doctors/", DoctorView.as_view(), name="doctors"),
    path("users/", UsersView.as_view(), name="users"),
    path("blogs/", BlogView.as_view(), name="blogs"),
    path("edit_blog/<int:id>", BlogView.as_view(), name="edit_blog"),
    path("bookings/", BookingsListView.as_view(), name="bookings"),
    path(
        "cancel_appointment/",
        CancelAppointmentView.as_view(),
        name="cancel_appointment",
    ),
]
