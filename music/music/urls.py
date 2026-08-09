from django.urls import path
from . import views

urlpatterns = [
    path("home/", views.home, name="home"),
]
# from django.urls import path
# from . import views

# urlpatterns = [
#     path("home/", views.home, name="home"),
# ]