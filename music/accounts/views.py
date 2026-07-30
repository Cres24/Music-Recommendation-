from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.contrib import messages

from .forms import LoginForm, UserRegistrationForm


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    authentication_form = LoginForm


def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully!")
            return redirect("login")
    else:
        form = UserRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})