from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from zoneinfo import ZoneInfo
from .models import Habit, HabitCompletion
from .forms import HabitForm


def _get_user_today(user):
    """Return today's date in the user's configured timezone."""
    try:
        from django.conf import settings
        tz_name = getattr(user.profile, 'timezone', None) if (user and hasattr(user, 'profile')) else None
        if not tz_name:
            tz_name = getattr(settings, 'TIME_ZONE', 'Asia/Kolkata')
        user_tz = ZoneInfo(tz_name)
    except Exception:
        user_tz = timezone.get_current_timezone()
    return timezone.now().astimezone(user_tz).date()


@login_required
def habit_list(request):
    habits = (
        Habit.objects.filter(user=request.user, is_archived=False)
        .prefetch_related('completions')
    )
    today = _get_user_today(request.user)

    habit_data = []
    for habit in habits:
        completed_today = habit.completions.filter(local_date=today).exists()
        streak = habit.get_current_streak()
        habit_data.append({
            'habit': habit,
            'completed_today': completed_today,
            'streak': streak,
        })

    context = {
        'habit_data': habit_data,
        'today': today,
        'active_count': habits.count(),
        'completed_today_count': sum(1 for h in habit_data if h['completed_today']),
    }
    return render(request, 'habits/habit_list.html', context)


@login_required
def habit_create(request):
    if request.method == 'POST':
        form = HabitForm(request.POST)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.save()
            from analytics.services import log_activity
            log_activity(
                user=request.user,
                event_type='HABIT_CREATED',
                title=habit.name,
                source_type='habit',
                source_id=habit.pk
            )
            messages.success(request, f'Habit "{habit.name}" created.')
            return redirect('habits:detail', pk=habit.pk)
    else:
        form = HabitForm()
    return render(request, 'habits/habit_form.html', {'form': form, 'title': 'Create Habit'})


@login_required
def habit_detail(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    today = _get_user_today(request.user)
    completed_today = habit.completions.filter(local_date=today).exists()
    streak = habit.get_current_streak()
    history = habit.get_completion_history(days=30)

    context = {
        'habit': habit,
        'today': today,
        'completed_today': completed_today,
        'streak': streak,
        'history': history,
    }
    return render(request, 'habits/habit_detail.html', context)


@login_required
def habit_update(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == 'POST':
        form = HabitForm(request.POST, instance=habit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Habit updated.')
            return redirect('habits:detail', pk=habit.pk)
    else:
        form = HabitForm(instance=habit)
    return render(request, 'habits/habit_form.html', {'form': form, 'habit': habit, 'title': 'Edit Habit'})


@login_required
def habit_complete(request, pk):
    """Toggle completion for today. Creates or deletes a HabitCompletion record."""
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == 'POST':
        today = _get_user_today(request.user)
        completion, created = HabitCompletion.objects.get_or_create(
            habit=habit, local_date=today
        )
        if not created:
            # Already completed today — uncomplete it
            completion.delete()
            messages.info(request, f'"{habit.name}" marked incomplete for today.')
        else:
            from gamification.services import award_xp, check_and_unlock_achievements
            from analytics.services import log_activity
            
            # Idempotency source_id combines habit id and date
            award_xp(
                user=request.user,
                source_type='habit',
                source_id=f"{habit.pk}_{today}",
                description=f'Completed habit: {habit.name} on {today}'
            )
            log_activity(
                user=request.user,
                event_type='HABIT_COMPLETED',
                title=f'Beacon lit: {habit.name}',
                source_type='habit',
                source_id=f"{habit.pk}_{today}"
            )
            check_and_unlock_achievements(request.user)
            messages.success(request, 'Another beacon lit.')

        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
    return redirect('habits:detail', pk=pk)


@login_required
def habit_archive(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == 'POST':
        habit.is_archived = True
        habit.save(update_fields=['is_archived', 'updated_at'])
        messages.success(request, f'Habit "{habit.name}" archived.')
        return redirect('habits:list')
    return render(request, 'habits/habit_confirm_archive.html', {'habit': habit})
