from django.shortcuts import render
from django.contrib.auth.views import LoginView

class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

def register(request):
    return render(request, "accounts/register.html")

# Create your views here.
