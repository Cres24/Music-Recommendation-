from django.urls import path
from .views import UserLoginView
from django.contrib.auth.views import LogoutView
from .views import register
from django.contrib.auth.views import LoginView

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path(
        "login/",
        LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("register/", register, name="register"),
]
