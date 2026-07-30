from django.contrib import admin

from .models import Album, Artist, Genre, ListeningHistory, Rating, Song, SongArtist


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "country")
    search_fields = ("name",)
    list_filter = ("country",)


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "artist", "release_year")
    search_fields = ("name",)
    list_filter = ("release_year",)


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "album", "genre", "duration")
    search_fields = ("title",)
    list_filter = ("genre",)


@admin.register(SongArtist)
class SongArtistAdmin(admin.ModelAdmin):
    list_display = ("id", "song", "artist", "role")
    list_filter = ("role",)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "song", "rating")
    list_filter = ("rating",)


@admin.register(ListeningHistory)
class ListeningHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "song", "played_at")
    list_filter = ("played_at",)
