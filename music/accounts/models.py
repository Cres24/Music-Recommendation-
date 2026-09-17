from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import User

class User(AbstractUser):
    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username



class Artist(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Album(models.Model):
    name = models.CharField(max_length=255)
    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name="albums"
    )

    def __str__(self):
        return self.name


class Song(models.Model):
    spotify_id = models.CharField(
        max_length=100,
        unique=True
    )

    title = models.CharField(max_length=255)

    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="songs"
    )

    genre = models.ForeignKey(
        Genre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="songs"
    )

    duration_ms = models.IntegerField()

    popularity = models.IntegerField(default=0)

    explicit = models.BooleanField(default=False)

    danceability = models.FloatField(default=0)

    energy = models.FloatField(default=0)

    loudness = models.FloatField(default=0)

    speechiness = models.FloatField(default=0)

    acousticness = models.FloatField(default=0)

    instrumentalness = models.FloatField(default=0)

    liveness = models.FloatField(default=0)

    valence = models.FloatField(default=0)

    tempo = models.FloatField(default=0)

    key = models.IntegerField(default=0)

    mode = models.IntegerField(default=0)

    time_signature = models.IntegerField(default=4)

    def __str__(self):
        return self.title
class SongArtist(models.Model):

    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE
    )

    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=50,
        default="Primary"
    )
class Rating(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE
    )

    rating = models.FloatField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )
class ListeningHistory(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE
    )

    played_at = models.DateTimeField(
        auto_now_add=True
    )