from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static
from core.views import OTPRequestView, OTPValidateView, UserView
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = (
    [
        path("api/users/", UserView.as_view()),
        path("api/users/otp/request/", OTPRequestView.as_view()),
        path("api/users/otp/validate/", OTPValidateView.as_view()),
        path("api/users/token/refresh/", TokenRefreshView.as_view()),
        path("api/buckets/", include("buckets.urls")),
    ]
    + static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
    + static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT,
    )
)
