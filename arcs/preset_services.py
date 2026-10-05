"""
Services for Winter Arc Preset Blueprints and Arc Activation.

Manages blueprint drafting, customization validation, and atomic creation of
Arc, Goal, Milestone, Task, and Habit records belonging strictly to the authenticated user.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, Tuple, Optional
from zoneinfo import ZoneInfo
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError

from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit
from analytics.services import log_activity
from core.presets import get_preset_by_key, PresetDefinition


def get_user_default_timezone(user) -> str:
    """Resolve the default timezone string for a user."""
    profile = getattr(user, 'profile', None)
    if profile and profile.timezone:
        return profile.timezone
    return getattr(settings, 'TIME_ZONE', 'Asia/Kolkata')


def get_user_today(user) -> date:
    """Return today's date in the user's configured timezone."""
    tz_name = get_user_default_timezone(user)
    try:
        user_tz = ZoneInfo(tz_name)
    except Exception:
        user_tz = timezone.get_current_timezone()
    return timezone.now().astimezone(user_tz).date()


def initialize_blueprint_draft(preset: PresetDefinition, user) -> Dict[str, Any]:
    """
    Initialize an editable blueprint draft from a PresetDefinition for a user.
    Sets default dates (start=today, end=today+recommended_duration) and user timezone.
    """
    start_date = get_user_today(user)
    duration_days = preset.recommended_duration_days or 90
    end_date = start_date + timedelta(days=duration_days)

    has_active_primary = user.arcs.filter(is_primary=True, status='ACTIVE').exists()

    draft = {
        'preset_key': preset.key,
        'preset_name': preset.name,
        'name': preset.name if preset.key != 'custom' else 'Winter Arc Protocol',
        'objective': preset.objective if preset.key != 'custom' else '',
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'recommended_duration_days': duration_days,
        'timezone': get_user_default_timezone(user),
        'is_primary': not has_active_primary,
        'goals': [g.to_dict() for g in preset.goals],
        'habits': [h.to_dict() for h in preset.habits],
    }
    return draft


def parse_date_str(val: Any) -> Optional[date]:
    """Helper to parse a date string or return date object."""
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val).strip(), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def validate_blueprint_draft(draft: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], Dict[str, str]]:
    """
    Validate a customized blueprint payload.
    Returns (is_valid, cleaned_data, errors).
    """
    errors: Dict[str, str] = {}
    cleaned: Dict[str, Any] = {}

    # 1. Arc Details
    name = str(draft.get('name', '')).strip()
    if not name:
        errors['name'] = 'Arc name cannot be blank.'
    elif len(name) > 255:
        errors['name'] = 'Arc name must be 255 characters or fewer.'
    cleaned['name'] = name

    objective = str(draft.get('objective', '')).strip()
    if not objective:
        errors['objective'] = 'Season objective cannot be blank. State your non-negotiable mission.'
    cleaned['objective'] = objective

    start_date = parse_date_str(draft.get('start_date'))
    end_date = parse_date_str(draft.get('end_date'))

    if not start_date:
        errors['start_date'] = 'Valid start date required (YYYY-MM-DD).'
    if not end_date:
        errors['end_date'] = 'Valid end date required (YYYY-MM-DD).'

    if start_date and end_date:
        if start_date > end_date:
            errors['start_date'] = 'Start date cannot be after end date.'
            errors['end_date'] = 'End date cannot be before start date.'
        cleaned['start_date'] = start_date
        cleaned['end_date'] = end_date

    tz_val = str(draft.get('timezone', 'UTC')).strip() or 'UTC'
    cleaned['timezone'] = tz_val
    cleaned['is_primary'] = bool(draft.get('is_primary', False))
    cleaned['preset_key'] = str(draft.get('preset_key', 'custom'))
    cleaned['preset_name'] = str(draft.get('preset_name', 'Custom Arc'))

    # 2. Goals Validation
    raw_goals = draft.get('goals', [])
    valid_categories = {'HEALTH', 'PRODUCTIVITY', 'LEARNING', 'FINANCE', 'OTHER'}
    cleaned_goals = []

    for i, g in enumerate(raw_goals):
        g_title = str(g.get('title', '')).strip()
        if not g_title:
            continue  # Skip blank goals
        g_cat = str(g.get('category', 'OTHER')).upper().strip()
        if g_cat not in valid_categories:
            g_cat = 'OTHER'
        try:
            g_priority = int(g.get('priority', 1))
            if g_priority not in (1, 2, 3):
                g_priority = 2
        except (ValueError, TypeError):
            g_priority = 2

        # Milestones in this goal
        raw_milestones = g.get('milestones', [])
        cleaned_milestones = []
        for m in raw_milestones:
            m_title = str(m.get('title', '')).strip()
            if not m_title:
                continue
            try:
                days_offset = int(m.get('days_offset', 30))
            except (ValueError, TypeError):
                days_offset = 30
            cleaned_milestones.append({
                'title': m_title,
                'target_value': m.get('target_value'),
                'days_offset': days_offset,
            })

        # Tasks in this goal
        raw_tasks = g.get('tasks', [])
        cleaned_tasks = []
        for t in raw_tasks:
            t_title = str(t.get('title', '')).strip()
            if not t_title:
                continue
            try:
                t_prio = int(t.get('priority', 2))
                if t_prio not in (1, 2, 3):
                    t_prio = 2
            except (ValueError, TypeError):
                t_prio = 2
            try:
                t_offset = int(t.get('days_offset', 3))
            except (ValueError, TypeError):
                t_offset = 3
            cleaned_tasks.append({
                'title': t_title,
                'description': str(t.get('description', '')).strip(),
                'priority': t_prio,
                'days_offset': t_offset,
            })

        cleaned_goals.append({
            'title': g_title,
            'description': str(g.get('description', '')).strip(),
            'category': g_cat,
            'priority': g_priority,
            'milestones': cleaned_milestones,
            'tasks': cleaned_tasks,
        })

    cleaned['goals'] = cleaned_goals

    # 3. Habits Validation
    raw_habits = draft.get('habits', [])
    valid_frequencies = {'DAILY', 'WEEKLY', 'SELECTED_DAYS', 'TARGET_COUNT'}
    cleaned_habits = []

    for h in raw_habits:
        h_name = str(h.get('name', '')).strip()
        if not h_name:
            continue
        h_freq = str(h.get('frequency', 'DAILY')).upper().strip()
        if h_freq not in valid_frequencies:
            h_freq = 'DAILY'
        try:
            h_target = int(h.get('target_count', 1))
            if h_target < 1:
                h_target = 1
        except (ValueError, TypeError):
            h_target = 1

        cleaned_habits.append({
            'name': h_name,
            'description': str(h.get('description', '')).strip(),
            'frequency': h_freq,
            'target_count': h_target,
            'target_label': str(h.get('target_label', f'{h_target} target')).strip(),
        })

    cleaned['habits'] = cleaned_habits

    is_valid = len(errors) == 0
    return is_valid, cleaned, errors


@transaction.atomic
def activate_blueprint_arc(user, cleaned_data: Dict[str, Any]) -> Arc:
    """
    Atomically creates the Arc, associated Goals, Milestones, Tasks, and Habits.
    Logs ARC_STARTED activity event without awarding completion XP.
    Enforces strict user ownership across all created entities.
    """
    start_date = cleaned_data['start_date']
    end_date = cleaned_data['end_date']
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    is_primary = cleaned_data.get('is_primary', False)
    if is_primary:
        # Clear existing primary flag for user's other arcs
        Arc.objects.filter(user=user, is_primary=True).update(is_primary=False)

    # 1. Create Arc
    arc = Arc.objects.create(
        user=user,
        name=cleaned_data['name'],
        objective=cleaned_data['objective'],
        start_date=start_date,
        end_date=end_date,
        status='ACTIVE',
        is_primary=is_primary,
        timezone=cleaned_data.get('timezone', 'UTC'),
    )

    # 2. Create Goals, Milestones, Tasks
    for goal_data in cleaned_data.get('goals', []):
        goal = Goal.objects.create(
            user=user,
            arc=arc,
            title=goal_data['title'],
            description=goal_data.get('description', ''),
            category=goal_data.get('category', 'OTHER'),
            priority=goal_data.get('priority', 1),
            status='PENDING',
            deadline=end_date,
        )

        # Milestones
        for m_data in goal_data.get('milestones', []):
            offset = m_data.get('days_offset', 30)
            m_due = start_date + timedelta(days=offset)
            if m_due > end_date:
                m_due = end_date
            Milestone.objects.create(
                goal=goal,
                title=m_data['title'],
                target_value=m_data.get('target_value'),
                due_date=m_due,
            )

        # Tasks
        for t_data in goal_data.get('tasks', []):
            t_offset = t_data.get('days_offset', 3)
            task_date = start_date + timedelta(days=t_offset)
            if task_date > end_date:
                task_date = end_date
            # Set time to 09:00 local representation
            due_dt = timezone.make_aware(
                datetime.combine(task_date, datetime.min.time().replace(hour=9))
            ) if timezone.is_naive(datetime.combine(task_date, datetime.min.time())) else datetime.combine(task_date, datetime.min.time().replace(hour=9))

            Task.objects.create(
                user=user,
                goal=goal,
                title=t_data['title'],
                description=t_data.get('description', ''),
                priority=t_data.get('priority', 2),
                status='PENDING',
                due_at=due_dt,
            )

    # 3. Create Habits
    for h_data in cleaned_data.get('habits', []):
        Habit.objects.create(
            user=user,
            name=h_data['name'],
            description=h_data.get('description', ''),
            frequency=h_data.get('frequency', 'DAILY'),
            target_count=h_data.get('target_count', 1),
            active_from=start_date,
            active_until=end_date,
            is_archived=False,
        )

    # 4. Log Arc Sworn Activity (Zero completion XP awarded)
    log_activity(
        user=user,
        event_type='ARC_STARTED',
        title=f'Sworn: {arc.name}',
        arc=arc,
        source_type='arc',
        source_id=arc.pk,
    )

    return arc
