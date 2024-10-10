from django.urls import path
from users import views


urlpatterns = [
    path("register/", views.Register.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="login"),
    path("doctors/", views.DoctorsView.as_view(), name="doctors"),
    path("booking/", views.BookingView.as_view(), name="booking"),
    path("patient_form/", views.PatientForm.as_view(), name="patient_form"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path(
        "appointment_list/",
        views.AppointmentsListView.as_view(),
        name="appointment_list",
    ),
    path(
        "contact_us/",
        views.ContactUsView.as_view(),
        name="contact_us",
    ),
    path(
        "edit_profile/",
        views.EditUser.as_view(),
        name="edit_profile",
    ),
    path(
        "otp_verification/",
        views.OTPVerification.as_view(),
        name="otp_verification",
    ),
    path(
        "reset_password/",
        views.ResetPasswordView.as_view(),
        name="reset_password",
    ),
    path(
        "reports/",
        views.ReportsView.as_view(),
        name="reports",
    ),
    path(
        "departments/",
        views.DepartmentsView.as_view(),
        name="departments",
    ),
    path(
        "reciepts/",
        views.Reciepts.as_view(),
        name="reciepts",
    ),
]
