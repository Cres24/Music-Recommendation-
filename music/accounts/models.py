from django.contrib.auth import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models

class User(AbstractUser):
    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username



class MusicPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="music_preference"
    )

    favorite_genre = models.CharField(max_length=50)

    song_priority = models.CharField(max_length=50)

    preferred_mood = models.CharField(max_length=50)

    listening_context = models.CharField(max_length=50)

    playlist_preference = models.CharField(max_length=50)

    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - Music Preferences"


class SpotifyToken(models.Model):
    """OAuth tokens for a connected Spotify account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="spotify_token",
    )
    access_token = models.CharField(max_length=512)
    refresh_token = models.CharField(max_length=512)
    expires_at = models.DateTimeField()
    scope = models.TextField(blank=True, default="")
    spotify_user_id = models.CharField(max_length=100, blank=True, default="")
    display_name = models.CharField(max_length=200, blank=True, default="")
    # "premium" | "free" | "open" — Web Playback SDK needs premium
    product = models.CharField(max_length=20, blank=True, default="")

    def __str__(self):
        return f"SpotifyToken({self.user.username})"
