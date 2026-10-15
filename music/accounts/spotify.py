"""Spotify Web API helpers.

- app token (client_credentials) for catalogue lookups (album art)
- OAuth authorize / code exchange / refresh for user actions
- REST helpers for the playback + playlist endpoints
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone

AUTH_BASE = "https://accounts.spotify.com"
API_BASE = "https://api.spotify.com/v1"
TIMEOUT = 10

_app_token = {"token": None, "expires_at": 0.0}


def _client_auth():
    return requests.auth.HTTPBasicAuth(
        settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET
    )


def _raise_for_spotify(response):
    """Raise with Spotify's error body so failures are diagnosable in logs.

    ``raise_for_status`` alone only reports "400 Bad Request" and drops the
    reason (invalid_client / invalid_grant / ...), which makes OAuth and API
    failures opaque. Re-raising with the body keeps that detail in the logs.
    """
    if response.status_code >= 400:
        raise requests.HTTPError(
            f"{response.status_code} {response.text}", response=response
        )
    return response


def app_token():
    """Application access token (no user), cached per process."""
    now = timezone.now()
    if _app_token["token"] and _app_token["expires_at"] > now:
        return _app_token["token"]
    response = requests.post(
        f"{AUTH_BASE}/api/token",
        auth=_client_auth(),
        data={"grant_type": "client_credentials"},
        timeout=TIMEOUT,
    )
    _raise_for_spotify(response)
    payload = response.json()
    _app_token["token"] = payload["access_token"]
    _app_token["expires_at"] = now + timedelta(seconds=payload["expires_in"])
    return _app_token["token"]


def authorize_url(state: str) -> str:
    return AUTH_BASE + "/authorize?" + urlencode({
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "scope": settings.SPOTIFY_SCOPES,
        "state": state,
    })


def exchange_code(code: str) -> dict:
    response = requests.post(
        f"{AUTH_BASE}/api/token",
        auth=_client_auth(),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        },
        timeout=TIMEOUT,
    )
    _raise_for_spotify(response)
    return response.json()


def _refresh(refresh_token: str) -> dict:
    response = requests.post(
        f"{AUTH_BASE}/api/token",
        auth=_client_auth(),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=TIMEOUT,
    )
    _raise_for_spotify(response)
    return response.json()


def ensure_fresh(token_row) -> str:
    """Return a valid access token, refreshing the row when expiring."""
    if timezone.now() < token_row.expires_at - timedelta(seconds=60):
        return token_row.access_token
    payload = _refresh(token_row.refresh_token)
    token_row.access_token = payload["access_token"]
    token_row.expires_at = timezone.now() + timedelta(
        seconds=payload.get("expires_in", 3600)
    )
    if payload.get("refresh_token"):
        token_row.refresh_token = payload["refresh_token"]
    token_row.save(update_fields=["access_token", "expires_at", "refresh_token"])
    return token_row.access_token


def _request(method, url, token, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.setdefault("Authorization", f"Bearer {token}")
    response = requests.request(
        method, url, headers=headers, timeout=TIMEOUT, **kwargs
    )
    return response


def user_get(token_row, path) -> dict:
    response = _request("GET", f"{API_BASE}{path}", ensure_fresh(token_row))
    _raise_for_spotify(response)
    return response.json()


def _track_art(token, track_id):
    """Return (track_id, image_url) for an existing track, (id, None) on 404."""
    response = _request("GET", f"{API_BASE}/tracks/{track_id}", token)
    if response.status_code == 404:
        # id removed from Spotify since the 2022 dataset was built
        return track_id, None
    _raise_for_spotify(response)
    images = response.json().get("album", {}).get("images") or []
    # prefer the 300px cover, fall back to whatever exists
    image = next(
        (i["url"] for i in images if i.get("height") == 300),
        images[0]["url"] if images else "",
    )
    return track_id, image


def fetch_tracks(track_ids) -> dict:
    """Look up album art with the app token, one request per id.

    Spotify removed the batch endpoint (GET /tracks?ids=) for Development-mode
    apps in the February 2026 Web API change, so ids are fetched individually
    (in parallel). Returns {track_id: image_url_or_empty} for ids that still
    exist; removed/bogus ids are simply absent from the mapping.
    """
    if not track_ids:
        return {}
    token = app_token()
    with ThreadPoolExecutor(max_workers=min(8, len(track_ids))) as pool:
        results = list(pool.map(lambda tid: _track_art(token, tid), track_ids))
    return {track_id: image for track_id, image in results if image is not None}


def create_playlist(token_row, name: str, uris: list, public: bool = False) -> str:
    """Create a playlist for the user, add the tracks, return its URL."""
    token = ensure_fresh(token_row)
    # POST /users/{id}/playlists was removed in Feb 2026; use /me/playlists.
    response = _request(
        "POST",
        f"{API_BASE}/me/playlists",
        token,
        json={
            "name": name,
            "public": public,
            "description": "Generated by the Music Recommendation app",
        },
    )
    _raise_for_spotify(response)
    playlist = response.json()

    if uris:  # 100 uri cap per call; our lists are 20
        # .../tracks was renamed to .../items in Feb 2026.
        response = _request(
            "POST",
            f"{API_BASE}/playlists/{playlist['id']}/items",
            token,
            json={"uris": uris},
        )
        _raise_for_spotify(response)

    return playlist["external_urls"]["spotify"]
