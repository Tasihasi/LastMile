from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import UserProfile
from ..serializers import UserSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username", "").strip()
    role = request.data.get("role", "biker").strip()

    if not username:
        return Response({"error": "Username is required."}, status=status.HTTP_400_BAD_REQUEST)
    if role not in ("biker", "planner"):
        return Response({"error": "Role must be 'biker' or 'planner'."}, status=status.HTTP_400_BAD_REQUEST)

    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_unusable_password()
        user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"role": role})
    if not created and profile.role != role:
        profile.role = role
        profile.save()

    token, _ = Token.objects.get_or_create(user=user)

    return Response(
        {
            "token": token.key,
            "user": UserSerializer(user).data,
        }
    )


@api_view(["GET"])
def me_view(request):
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
def logout_view(request):
    Token.objects.filter(user=request.user).delete()
    return Response({"message": "Logged out."})
