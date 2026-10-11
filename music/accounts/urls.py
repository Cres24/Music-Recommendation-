# from django.urls import path
# from django.contrib.auth.views import LogoutView
# from .views import UserLoginView, register

# urlpatterns = [
#     path("login/", UserLoginView.as_view(), name="login"),
#     path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
#     path("register/", register, name="register"),
# ]
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
        path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html"
        ),
        name="login",
    ),
    path(
    "preferences/",
    views.music_preferences,
    name="music_preferences"
    ),
    path("spotify/connect/", views.spotify_connect, name="spotify_connect"),
    path("spotify/callback/", views.spotify_callback, name="spotify_callback"),
    path("spotify/token/", views.spotify_token, name="spotify_token"),
    path("spotify/disconnect/", views.spotify_disconnect, name="spotify_disconnect"),
]