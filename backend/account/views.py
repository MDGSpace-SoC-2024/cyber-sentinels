from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .serializers import UserSerializer
from django.contrib.auth.views import PasswordResetView
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib.auth import logout, login
from django.contrib.auth.hashers import make_password
import secrets
import string
import re
from .models import MasterHash
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def get_master_password(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    master = MasterHash.objects.get(user=request.user)
    hashed_master_password = master.hash
    salt = master.salt
    email = request.user.email
    return JsonResponse(
        {"hashedMasterPassword": hashed_master_password, "salt": salt, "email": email}
    )


def generate(length=16, lowercase=True, uppercase=True, numbers=True, symbols=True):
    characters = string.ascii_lowercase
    if uppercase:
        characters += string.ascii_uppercase
    if numbers:
        characters += string.digits
    if symbols:
        characters += string.punctuation
    pattern = r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s])"
    password = ""
    while not (
        any([char in password for char in string.ascii_lowercase])
        and any([char in password for char in string.ascii_uppercase])
        and any([char in password for char in string.digits])
        and any([char in password for char in string.punctuation])
        and re.search(pattern, password)
    ):
        password = "".join(secrets.choice(characters) for _ in range(length))

    return password


def index(request):
    return render(request, "account/index.html")


@api_view(["POST"])
def register_user(request):
    if request.method == "POST":
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            hash = make_password(generate(20), salt=generate(20))
            MasterHash.objects.create(user=user, hash=hash, salt=generate(20))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def user_login(request):
    if request.method == "POST":
        username = request.data.get("username")
        password = request.data.get("password")

        if "@" in username:
            user = User.objects.filter(email=username).first()

            if user:
                if user.check_password(password):
                    login(request, user)
                    token, _ = Token.objects.get_or_create(user=user)
                    return Response({"token": token.key}, status=status.HTTP_200_OK)

        else:
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                token, _ = Token.objects.get_or_create(user=user)
                return Response({"token": token.key}, status=status.HTTP_200_OK)

        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def user_logout(request):
    try:
        logout(request)
        if hasattr(request.auth, "delete"):
            request.auth.delete()
        return Response(
            {"message": "Successfully logged out."}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        email = form.cleaned_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            register_url = reverse("auth")
            error_message = 'Email address not found. Please  <a style="color: #0000FF" href="{}">Register</a>'.format(
                register_url
            )
            messages.error(self.request, mark_safe(error_message))
            return self.form_invalid(form)

        return super().form_valid(form)


from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


def my_view(request):
    user = request.user

    if user.is_authenticated:
        return HttpResponse(f"Hello, {user.username}! You are logged in.")
    else:
        return HttpResponse("You are not logged in.")


from django.http import JsonResponse
from django.middleware.csrf import get_token

def get_csrf_token(request):
    csrf_token = get_token(request)
    return JsonResponse({'csrf_token': csrf_token})