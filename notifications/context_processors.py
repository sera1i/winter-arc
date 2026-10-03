from .services import get_unread_count

def notification_context(request):
    """
    Context processor providing the unread notification count across all templates.
    """
    if request.user.is_authenticated:
        return {
            'unread_notifications_count': get_unread_count(request.user)
        }
    return {
        'unread_notifications_count': 0
    }
