from rest_framework import views
from rest_framework.request import Request
from rest_framework.response import Response
from core.models import FileshipUser
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from datetime import datetime, timedelta
from rest_framework.permissions import AllowAny


class UserView(views.APIView):
    def get(self, request: Request):
        user = request.user
        fuser = FileshipUser.objects.get(user=user)
        return Response(
            {
                "user": fuser.representation(),
            }
        )


class OTPRequestView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request):
        data = request.data
        email = data.get("email")
        fuser = FileshipUser.get_from_email(email)
        fuser.send_otp()

        return Response(
            {
                "status": "success",
            }
        )


class OTPValidateView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request):
        data = request.data
        email = data.get("email")
        otp = data.get("otp")

        try:
            fuser = FileshipUser.objects.get(
                user__email=email,
                otp=otp,
                otp_at__gte=datetime.now() - timedelta(minutes=5),
            )
        except FileshipUser.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": "Invalid OTP",
                },
                status=400,
            )
        fuser.clear_otp()
        user = fuser.user

        return Response(
            {
                "user": fuser.representation(),
                "token": {
                    "access": str(AccessToken.for_user(user)),
                    "refresh": str(RefreshToken.for_user(user)),
                },
            }
        )
