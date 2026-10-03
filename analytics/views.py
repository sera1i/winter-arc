from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .progress_services import get_full_analytics_summary
from gamification.models import Achievement, UserAchievement

@login_required
def analytics_dashboard(request):
    arc_id = request.GET.get('arc_id')
    analytics_data = get_full_analytics_summary(request.user, arc_id=arc_id)
    
    # Achievements
    user_achievements = UserAchievement.objects.filter(user=request.user).select_related('achievement')
    all_achievements = Achievement.objects.all()
    unlocked_ids = set(user_achievements.values_list('achievement_id', flat=True))

    achievements_display = []
    for ach in all_achievements:
        achievements_display.append({
            'achievement': ach,
            'is_unlocked': ach.id in unlocked_ids,
        })

    context = {
        **analytics_data,
        'user_achievements': user_achievements,
        'achievements_display': achievements_display,
    }
    return render(request, 'analytics/analytics_dashboard.html', context)
