from ..models import DeliverySession


def get_user_session(request, session_id):
    """Get a session, enforcing ownership for bikers."""
    try:
        session = DeliverySession.objects.get(id=session_id)
    except DeliverySession.DoesNotExist:
        return None

    # Planners can access any session (including unowned)
    if hasattr(request.user, "profile") and request.user.profile.role == "planner":
        return session
    # Bikers can only access sessions they own
    if session.owner == request.user:
        return session
    return None


def require_planner(request):
    return hasattr(request.user, "profile") and request.user.profile.role == "planner"
