from django.urls import path

from . import views

urlpatterns = [
    path("upload/", views.upload_file, name="upload-file"),
    path("sessions/<uuid:session_id>/", views.get_session, name="get-session"),
    path("sessions/<uuid:session_id>/geocode/", views.geocode_stops, name="geocode-stops"),
    path("sessions/<uuid:session_id>/geocode-status/", views.geocode_status, name="geocode-status"),
    path("sessions/<uuid:session_id>/optimize/", views.optimize, name="optimize"),
]
