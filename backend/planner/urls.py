from django.urls import path

from . import views

urlpatterns = [
    # Auth
    path("auth/login/", views.login_view, name="auth-login"),
    path("auth/me/", views.me_view, name="auth-me"),
    path("auth/logout/", views.logout_view, name="auth-logout"),
    # Planner
    path("users/bikers/", views.list_bikers, name="list-bikers"),
    # Sessions
    path("sessions/", views.list_sessions, name="list-sessions"),
    path("upload/", views.upload_file, name="upload-file"),
    path("sessions/<uuid:session_id>/", views.get_session, name="get-session"),
    path("sessions/<uuid:session_id>/geocode/", views.geocode_stops, name="geocode-stops"),
    path("sessions/<uuid:session_id>/geocode-status/", views.geocode_status, name="geocode-status"),
    path("sessions/<uuid:session_id>/optimize/", views.optimize, name="optimize"),
    path("sessions/<uuid:session_id>/share/", views.share_session, name="share-session"),
    path("sessions/<uuid:session_id>/delete/", views.delete_session, name="delete-session"),
    path("sessions/<uuid:session_id>/assign/", views.assign_session, name="assign-session"),
    path("sessions/<uuid:session_id>/start/", views.start_route, name="start-route"),
    path("sessions/<uuid:session_id>/stops/<int:stop_id>/status/", views.update_stop_status, name="update-stop-status"),
    # Public sharing
    path("shared/<uuid:share_id>/", views.get_shared_route, name="get-shared-route"),
]
