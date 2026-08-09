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

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]