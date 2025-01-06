from django.urls import path, include
from core.views import OTPRequestView, OTPValidateView, UserView
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path("srv/api/users/", UserView.as_view()),
    path("srv/api/users/otp/request/", OTPRequestView.as_view()),
    path("srv/api/users/otp/validate/", OTPValidateView.as_view()),
    path("srv/api/users/token/refresh/", TokenRefreshView.as_view()),
    path("srv/api/buckets/", include("buckets.urls")),
]
