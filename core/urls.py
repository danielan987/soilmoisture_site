from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("healthz/", views.healthz, name="healthz"),
    path("", views.index, name="index"),
    path("geocode/", views.geocode_view, name="geocode"),
    path("power/", views.power_view, name="power"),
    path("forecast/", views.forecast_view, name="forecast"),
]
