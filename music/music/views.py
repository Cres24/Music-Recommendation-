import logging
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import requests
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import MusicPreference, SpotifyToken
from accounts import spotify as spotify_api
from .models import SpotifyTrack
from .personalize import answers_from_preference, summary_from_preference

logger = logging.getLogger(__name__)

# The recommendation engine lives outside the Django apps (machine/).
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "machine"))
import recommender  # noqa: E402

SPOTIFY_MESSAGES = {
    "connected": (
        "success",
        "Spotify connected — press any song to play, or save this list as a playlist.",
    ),
    "disconnected": ("info", "Spotify disconnected."),
    "denied": ("danger", "Spotify connection was cancelled or denied."),
    "bad_state": ("danger", "Spotify connection failed verification. Please try again."),
    "auth_failed": ("danger", "Spotify connection failed. Please try again."),
    "not_connected": ("danger", "Connect your Spotify account first."),
}

PLAYLIST_ERRORS = {
    "engine": "Couldn't rebuild your recommendations for the playlist. Please try again.",
    "empty": "None of these tracks are available on Spotify right now.",
    "api": "Spotify request failed. Please try again.",
}

SPOTIFY_HTTP_ERRORS = {
    400: "Spotify rejected the request. Try disconnecting and reconnecting.",
    401: "Your Spotify session expired. Disconnect and reconnect Spotify.",
    403: "Spotify denied this action. Try reconnecting your account.",
    429: "Spotify is rate limiting requests — wait a minute and try again.",
}


def decorate_tracks(results):
    """Attach album art + availability to results via the SpotifyTrack cache.

    One batched /v1/tracks call per page view the first time a track is
    shown; every later render is served straight from the database.
    """
    ids = [r["track_id"] for r in results if r.get("track_id")]
    cached = {}
    try:
        cached = {
            t.track_id: t for t in SpotifyTrack.objects.filter(track_id__in=ids)
        }
        missing = [t for t in ids if t not in cached]
        for start in range(0, len(missing), 50):  # API cap: 50 ids per call
            chunk = missing[start:start + 50]
            try:
                lookup = spotify_api.fetch_tracks(chunk)
            except Exception:
                # Don't cache failures — we just skip art for this render.
                logger.exception("spotify track lookup failed")
                continue
            rows = [
                SpotifyTrack(
                    track_id=tid,
                    image_url=lookup.get(tid, ""),
                    found=tid in lookup,
                )
                for tid in chunk
            ]
            SpotifyTrack.objects.bulk_create(rows, ignore_conflicts=True)
            cached.update({row.track_id: row for row in rows})
    except Exception:
        logger.exception("album art decoration failed")

    for result in results:
        row = cached.get(result.get("track_id"))
        result["image_url"] = row.image_url if row else ""
        result["available"] = row.found if row else True
    return results


def _banner_from_params(params):
    if "playlist_url" in params:
        url = params.get("playlist_url", "")
        if not url.startswith("https://open.spotify.com/"):
            url = ""
        name = params.get("playlist_name", "your playlist")
        return {
            "kind": "success",
            "text": f"“{name}” was saved to your Spotify.",
            "url": url,
        }
    if "playlist_error" in params:
        code = params.get("playlist_error", "")
        text = PLAYLIST_ERRORS.get(code) or SPOTIFY_HTTP_ERRORS.get(
            int(code) if code.isdigit() else 0
        )
        return {"kind": "danger", "text": text or PLAYLIST_ERRORS["api"]}
    if "spotify" in params:
        kind, text = SPOTIFY_MESSAGES.get(params["spotify"], ("info", ""))
        return {"kind": kind, "text": text} if text else None
    return None


def _redirect_home(**params):
    return redirect(reverse("home") + "?" + urlencode(params))


@login_required
def home(request):
    preference = MusicPreference.objects.filter(
        user=request.user, completed=True
    ).first()
    if preference is None:
        return redirect("music_preferences")

    answers = answers_from_preference(preference)
    token_row = SpotifyToken.objects.filter(user=request.user).first()
    context = {
        "summary": summary_from_preference(preference),
        "answers": answers,
        "banner": _banner_from_params(request.GET),
        "spotify_connected": token_row is not None,
        "spotify_product": token_row.product if token_row else "",
    }
    try:
        results, meta = recommender.recommend(answers, k=20)
        context["results"] = decorate_tracks(results)
        context["candidate_count"] = meta["candidates"]
    except Exception:
        logger.exception("recommendation failed for user %s", request.user.username)
        context["error"] = (
            "We couldn't build your recommendations right now. Please try again later."
        )

    return render(request, "home.html", context)


@login_required
@require_POST
def create_playlist(request):
    """Save the current 20 recommendations as a playlist on Spotify."""
    token_row = SpotifyToken.objects.filter(user=request.user).first()
    if token_row is None:
        return _redirect_home(spotify="not_connected")

    preference = MusicPreference.objects.filter(
        user=request.user, completed=True
    ).first()
    if preference is None:
        return redirect("music_preferences")

    name = request.POST.get("playlist_name", "").strip() or (
        f"Recommendations \u2013 {date.today().isoformat()}"
    )

    try:
        answers = answers_from_preference(preference)
        results, _ = recommender.recommend(answers, k=20)
    except Exception:
        logger.exception("playlist rebuild failed for %s", request.user.username)
        return _redirect_home(playlist_error="engine")

    decorate_tracks(results)
    uris = [
        f"spotify:track:{result['track_id']}"
        for result in results
        if result.get("track_id") and result.get("available", True)
    ]
    if not uris:
        return _redirect_home(playlist_error="empty")

    try:
        url = spotify_api.create_playlist(token_row, name, uris)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 0
        logger.warning("playlist creation failed (%s) for %s", status, request.user.username)
        return _redirect_home(playlist_error=str(status))
    except Exception:
        logger.exception("playlist creation errored for %s", request.user.username)
        return _redirect_home(playlist_error="api")

    return _redirect_home(playlist_url=url, playlist_name=name)
