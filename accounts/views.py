from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from zoneinfo import ZoneInfo
from .forms import CustomUserCreationForm, ProfileUpdateForm
from .models import Profile

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing/index.html')

def _get_user_today(user):
    try:
        from django.conf import settings
        tz_name = getattr(user.profile, 'timezone', None) if (user and hasattr(user, 'profile')) else None
        if not tz_name:
            tz_name = getattr(settings, 'TIME_ZONE', 'Asia/Kolkata')
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.get_current_timezone()
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
    from goals.models import Goal

    user = request.user
    today = _get_user_today(user)

    # Arcs: Primary arc
    primary_arc = Arc.objects.filter(user=user, is_primary=True).exclude(status='ARCHIVED').first()
    active_arcs_qs = Arc.objects.filter(user=user, status='ACTIVE')
    active_arcs = active_arcs_qs.count()

    # Goals: display goals for the primary arc
    if primary_arc:
        goals = primary_arc.goals.all().prefetch_related('milestones')
    else:
        goals = []

    # Tasks: pending & in-progress tasks display immediately
    pending_tasks = Task.objects.filter(
        user=user, status__in=['PENDING', 'IN_PROGRESS']
    ).select_related('goal').order_by('priority', 'due_at')[:8]

    today_completed_tasks = Task.objects.filter(
        user=user, status='COMPLETED', completed_at__date=today
    ).count()
    total_pending_count = Task.objects.filter(user=user, status__in=['PENDING', 'IN_PROGRESS']).count()

    # Habits (evaluated via in-memory prefetch to avoid N+1 queries)
    active_habits = list(Habit.objects.filter(user=user, is_archived=False).prefetch_related('completions'))
    habit_data = []
    for habit in active_habits:
        completed_dates = {c.local_date for c in habit.completions.all()}
        completed_today = today in completed_dates
        habit_data.append({'habit': habit, 'completed_today': completed_today, 'streak': habit.get_current_streak()})
    habits_done_today = sum(1 for h in habit_data if h['completed_today'])
    top_streaks = sorted(habit_data, key=lambda x: x['streak'], reverse=True)[:3]

    # Progress and Gamification metrics from real persisted data
    from gamification.services import get_user_rank, get_user_total_xp
    from analytics.progress_services import calculate_arc_progress
    from analytics.models import ActivityEvent
    from journal.models import JournalEntry

    rank_info = get_user_rank(user)
    total_xp = get_user_total_xp(user)
    arc_progress = calculate_arc_progress(primary_arc) if primary_arc else 0
    recent_activity = ActivityEvent.objects.filter(user=user)[:5]
    today_journal_entry = JournalEntry.objects.filter(user=user, local_date=today).first()

    context = {
        'primary_arc': primary_arc,
        'active_arcs': active_arcs,
        'arc_progress': arc_progress,
        'rank_info': rank_info,
        'total_xp': total_xp,
        'goals': goals,
        'pending_tasks': pending_tasks,
        'total_pending_count': total_pending_count,
        'today_completed_tasks': today_completed_tasks,
        'habit_data': habit_data[:6],
        'habits_done_today': habits_done_today,
        'total_habits': len(active_habits),
        'top_streaks': top_streaks,
        'today': today,
        'recent_activity': recent_activity,
        'today_journal_entry': today_journal_entry,
    }
    return render(request, 'accounts/dashboard.html', context)
