from django.shortcuts import render, redirect
from django.contrib import messages
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


# ---------------------------------------------------------------------------
# Spotify connection (OAuth + token endpoint for the browser player)
# ---------------------------------------------------------------------------

import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone

from . import spotify as spotify_service
from .models import SpotifyToken

spotify_logger = logging.getLogger(__name__)


def _home(param: str):
    return redirect(reverse("home") + "?" + urlencode({"spotify": param}))


@login_required
def spotify_connect(request):
    state = secrets.token_urlsafe(16)
    request.session["spotify_state"] = state
    return redirect(spotify_service.authorize_url(state))


@login_required
def spotify_callback(request):
    if request.GET.get("error"):
        return _home("denied")
    state = request.GET.get("state", "")
    if not state or state != request.session.pop("spotify_state", ""):
        return _home("bad_state")
    code = request.GET.get("code", "")
    if not code:
        return _home("auth_failed")

    try:
        payload = spotify_service.exchange_code(code)
        existing = SpotifyToken.objects.filter(user=request.user).first()
        refresh_token = payload.get("refresh_token") or (
            existing.refresh_token if existing else ""
        )
        if not refresh_token:
            return _home("auth_failed")

        token_row = existing or SpotifyToken(user=request.user)
        token_row.access_token = payload["access_token"]
        token_row.refresh_token = refresh_token
        token_row.expires_at = timezone.now() + timedelta(
            seconds=payload.get("expires_in", 3600)
        )
        token_row.scope = payload.get("scope", "")

        me = spotify_service.user_get(token_row, "/me")
        token_row.spotify_user_id = me["id"]
        token_row.display_name = me.get("display_name", "")
        token_row.product = me.get("product", "")
        token_row.save()
    except Exception:
        spotify_logger.exception(
            "spotify oauth failed for %s", request.user.username
        )
        return _home("auth_failed")
    return _home("connected")


def spotify_token(request):
    """Fresh access token for the Web Playback SDK (browser fetches this)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "not authenticated"}, status=401)
    token_row = SpotifyToken.objects.filter(user=request.user).first()
    if token_row is None:
        return JsonResponse({"error": "not connected"}, status=404)
    try:
        token = spotify_service.ensure_fresh(token_row)
    except Exception:
        spotify_logger.exception("token refresh failed for %s", request.user.username)
        return JsonResponse({"error": "refresh failed"}, status=502)
    remaining = int((token_row.expires_at - timezone.now()).total_seconds())
    return JsonResponse({
        "access_token": token,
        "expires_in": max(remaining, 0),
        "product": token_row.product,
    })


@login_required
def spotify_disconnect(request):
    SpotifyToken.objects.filter(user=request.user).delete()
    return _home("disconnected")