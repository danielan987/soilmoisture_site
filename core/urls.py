from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.index, name="index"),
    path("power/", views.power_view, name="power"),          # HTMX partial: table
    path("forecast/", views.forecast_view, name="forecast"),  # HTMX partial: chart
    path("geocode/", views.geocode_view, name="geocode"),     # JSON response used by app.js
]
