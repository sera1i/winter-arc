from django.db import transaction
from .models import ActivityEvent

def log_activity(user, event_type, title, description='', arc=None, source_type='', source_id='', metadata=None):
    """
    Log a meaningful user activity event safely, deterministically, and idempotently.
    If source_type and source_id are provided, prevents duplicate event logging.
    """
    if metadata is None:
        metadata = {}
    
    sid_str = str(source_id) if source_id else ''
    if source_type and sid_str:
        event, created = ActivityEvent.objects.get_or_create(
            user=user,
            event_type=event_type,
            source_type=source_type,
            source_id=sid_str,
            defaults={
                'arc': arc,
                'title': title,
                'description': description,
                'metadata': metadata,
            }
        )
        return event
    else:
        return ActivityEvent.objects.create(
            user=user,
            arc=arc,
            event_type=event_type,
            title=title,
            description=description,
            source_type=source_type,
            source_id=sid_str,
            metadata=metadata
        )

def get_recent_activity(user, arc=None, limit=10):
    """
    Retrieve the authenticated user's recent activity events, optionally scoped to an Arc.
    """
    qs = ActivityEvent.objects.filter(user=user)
    if arc:
        qs = qs.filter(arc=arc)
    return qs.select_related('arc')[:limit]
