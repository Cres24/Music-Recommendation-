from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm
from .forms import MusicPreferenceForm
from .models import MusicPreference


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("music_preferences")   # Redirect after registration
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")   # Redirect after login
    else:
        form = AuthenticationForm()

    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect




@login_required
def music_preferences(request):

    preference, created = MusicPreference.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        form = MusicPreferenceForm(
            request.POST,
            instance=preference
        )

        if form.is_valid():

            preference = form.save(commit=False)

            preference.user = request.user
            preference.completed = True

            preference.save()

            return redirect("home")

    else:

        form = MusicPreferenceForm(
            instance=preference
        )

    return render(
        request,
        "accounts/music_preferences.html",
        {
            "form": form
        }
    )