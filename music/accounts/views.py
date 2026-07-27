from django.shortcuts import render
from django.contrib.auth.views import LoginView

class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

# Create your views here.
