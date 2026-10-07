from django.urls import path
from . import views

urlpatterns = [
    path("home/", views.home, name="home"),
    path("playlist/create/", views.create_playlist, name="create_playlist"),
]
# from django.urls import path
# from . import views

# urlpatterns = [
#     path("home/", views.home, name="home"),
# ]