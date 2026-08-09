# from django.shortcuts import render, redirect
# from django.contrib.auth.views import LoginView
# from django.contrib import messages

# from .forms import LoginForm, UserRegistrationForm


# class UserLoginView(LoginView):
#     template_name = "accounts/login.html"
#     redirect_authenticated_user = True
#     authentication_form = LoginForm


# def register(request):
#     if request.method == "POST":
#         form = UserRegistrationForm(request.POST)

#         if form.is_valid():
#             form.save()
#             messages.success(request, "Account created successfully!")
#             return redirect("login")
#     else:
#         form = UserRegistrationForm()

#     return render(request, "accounts/register.html", {"form": form})
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm

from .forms import RegisterForm


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")   # Redirect after registration
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")   # Redirect after login
    else:
        form = AuthenticationForm()

    return render(request, "registration/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")