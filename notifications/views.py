from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse

from .models import Notification
from .services import (
    get_or_create_user_preferences,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    get_unread_count
)
from .forms import NotificationPreferenceForm

@login_required
def notification_list(request):
    """
    Display paginated list of user's notifications.
    Supports filtering by unread status.
    """
    filter_type = request.GET.get('filter', 'all')
    queryset = Notification.objects.filter(user=request.user)

    if filter_type == 'unread':
        queryset = queryset.filter(is_read=False)

    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filter_type': filter_type,
        'unread_count': get_unread_count(request.user),
    }
    return render(request, 'notifications/notification_list.html', context)


@login_required
@require_POST
def mark_read(request, notification_id):
    """
    Mark single notification as read.
    Guarantees user ownership isolation.
    """
    success = mark_notification_as_read(request.user, notification_id)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({'success': success, 'unread_count': get_unread_count(request.user)})
    
    return redirect('notifications:list')


@login_required
@require_POST
def mark_all_read(request):
    """
    Mark all unread notifications for current user as read.
    """
    updated_count = mark_all_notifications_as_read(request.user)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({'success': True, 'updated': updated_count, 'unread_count': 0})

    messages.success(request, f"Marked {updated_count} notifications as read.")
    return redirect('notifications:list')


@login_required
def preferences_view(request):
    """
    View and update notification preferences.
    """
    prefs = get_or_create_user_preferences(request.user)
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=prefs)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification preferences updated.")
            return redirect('notifications:preferences')
    else:
        form = NotificationPreferenceForm(instance=prefs)

    context = {
        'form': form,
        'prefs': prefs,
    }
    return render(request, 'notifications/preferences.html', context)
