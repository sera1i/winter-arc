from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from zoneinfo import ZoneInfo
from .forms import CustomUserCreationForm, ProfileUpdateForm
from .models import Profile


def _get_user_today(user):
    try:
        tz = ZoneInfo(user.profile.timezone or 'UTC')
    except Exception:
        tz = ZoneInfo('UTC')
    return timezone.now().astimezone(tz).date()


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, "Registration successful. Welcome to Winter Arc!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def dashboard_view(request):
    from tasks.models import Task
    from habits.models import Habit, HabitCompletion
    from arcs.models import Arc

    user = request.user
    today = _get_user_today(user)

    # Arc
    primary_arc = Arc.objects.filter(user=user, is_primary=True).first()
    active_arcs = Arc.objects.filter(user=user, status='ACTIVE').count()

    # Tasks
    pending_tasks = Task.objects.filter(
        user=user, status='PENDING'
    ).select_related('goal').order_by('priority', 'due_at')[:5]
    today_completed_tasks = Task.objects.filter(
        user=user, status='COMPLETED', completed_at__date=today
    ).count()
    total_pending_count = Task.objects.filter(user=user, status='PENDING').count()

    # Habits
    active_habits = Habit.objects.filter(user=user, is_archived=False).prefetch_related('completions')
    habit_data = []
    for habit in active_habits:
        completed_today = habit.completions.filter(local_date=today).exists()
        habit_data.append({'habit': habit, 'completed_today': completed_today, 'streak': habit.get_current_streak()})
    habits_done_today = sum(1 for h in habit_data if h['completed_today'])
    top_streaks = sorted(habit_data, key=lambda x: x['streak'], reverse=True)[:3]

    context = {
        'primary_arc': primary_arc,
        'active_arcs': active_arcs,
        'pending_tasks': pending_tasks,
        'total_pending_count': total_pending_count,
        'today_completed_tasks': today_completed_tasks,
        'habit_data': habit_data[:4],
        'habits_done_today': habits_done_today,
        'total_habits': active_habits.count(),
        'top_streaks': top_streaks,
        'today': today,
    }
    return render(request, 'accounts/dashboard.html', context)
