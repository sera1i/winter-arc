from django.shortcuts import render
from django.urls import reverse


def focus_view(request):
    """
    Renders standalone Focus Mode experience with safe return_url state restoration.
    """
    default_return = reverse('dashboard')
    return_url = request.GET.get('return_url') or request.META.get('HTTP_REFERER') or default_return
    # Ensure return_url is a safe relative application path
    if not isinstance(return_url, str) or not return_url.startswith('/') or return_url.startswith('//'):
        return_url = default_return
    return render(request, 'focus/index.html', {'return_url': return_url})
