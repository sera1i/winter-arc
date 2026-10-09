from django.shortcuts import render


def focus_view(request):
    """
    Renders standalone Focus Mode experience.
    """
    return render(request, 'focus/index.html')
