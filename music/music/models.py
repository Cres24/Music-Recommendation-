from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "genres"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Artist(models.Model):
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100, blank=True)
    biography = models.TextField(blank=True)
    image = models.URLField(blank=True)

    class Meta:
        db_table = "artists"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Album(models.Model):
    name = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="albums")
    release_year = models.IntegerField()

    class Meta:
        db_table = "albums"
        ordering = ["-release_year", "name"]

    def __str__(self):
        return f"{self.name} — {self.artist.name}"


class Song(models.Model):
    title = models.CharField(max_length=300)
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="songs")
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, related_name="songs")
    duration = models.IntegerField(help_text="Duration in seconds")
    release_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "songs"
        ordering = ["title"]

    def __str__(self):
        return self.title


class SongArtist(models.Model):
    ROLE_CHOICES = [
        ("primary", "Primary"),
        ("featured", "Featured"),
        ("remix", "Remix"),
        ("producer", "Producer"),
    ]

    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="song_artists")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="artist_songs")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="primary")

    class Meta:
        db_table = "song_artists"
        constraints = [
            models.UniqueConstraint(fields=["song", "artist"], name="unique_song_artist"),
        ]

    def __str__(self):
        return f"{self.artist.name} ({self.role}) — {self.song.title}"


class Rating(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings")
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="ratings")
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        db_table = "ratings"
        constraints = [
            models.UniqueConstraint(fields=["user", "song"], name="unique_user_song_rating"),
        ]

    def __str__(self):
        return f"{self.user.username} rated {self.song.title}: {self.rating}"


class ListeningHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listening_history")
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="listen_events")
    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "listening_history"
        ordering = ["-played_at"]

    def __str__(self):
        return f"{self.user.username} listened to {self.song.title} at {self.played_at}"
