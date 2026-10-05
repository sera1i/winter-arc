from django.db import transaction
from django.db.models import Sum
from .models import XPEvent, Achievement, UserAchievement

# Deterministic XP Rule Constants
XP_TASK_COMPLETED = 15
XP_HABIT_COMPLETED = 15
XP_MILESTONE_COMPLETED = 50
XP_GOAL_COMPLETED = 100
XP_JOURNAL_COMPLETED = 20
XP_ARC_COMPLETED = 300

XP_RULES = {
    'task': XP_TASK_COMPLETED,
    'habit': XP_HABIT_COMPLETED,
    'milestone': XP_MILESTONE_COMPLETED,
    'goal': XP_GOAL_COMPLETED,
    'journal': XP_JOURNAL_COMPLETED,
    'arc': XP_ARC_COMPLETED,
}

# Master Rank Definitions (from Winter Arc Ice & Fire direction)
# Recruit -> Sentinel -> Ranger -> Warden
RANKS = [
    {'name': 'Recruit', 'min_xp': 0, 'max_xp': 299, 'level': 1},
    {'name': 'Sentinel', 'min_xp': 300, 'max_xp': 899, 'level': 2},
    {'name': 'Ranger', 'min_xp': 900, 'max_xp': 1999, 'level': 3},
    {'name': 'Warden', 'min_xp': 2000, 'max_xp': None, 'level': 4},
]

def award_xp(user, source_type, source_id, amount=None, description='', arc=None):
    """
    Award XP idempotently using the unique constraint (user, source_type, source_id).
    Returns (XPEvent, created: bool).
    If the event already exists, returns (existing_event, False) without duplicating XP.
    """
    if amount is None:
        amount = XP_RULES.get(source_type, 0)
    
    with transaction.atomic():
        event, created = XPEvent.objects.get_or_create(
            user=user,
            source_type=source_type,
            source_id=str(source_id),
            defaults={
                'amount': amount,
                'description': description or f"XP for {source_type} #{source_id}",
                'arc': arc,
            }
        )
        if created and event.arc is None and arc is not None:
            event.arc = arc
            event.save(update_fields=['arc'])
    return event, created

def get_user_total_xp(user, arc=None):
    """
    Calculate the user's total verified XP from the persistent ledger.
    Optionally scoped to an Arc.
    """
    qs = XPEvent.objects.filter(user=user)
    if arc:
        qs = qs.filter(arc=arc)
    total = qs.aggregate(total=Sum('amount'))['total']
    return total or 0

def get_user_rank(user):
    """
    Determine the user's deterministic rank based on total verified XP across all activity.
    Returns a dict with:
      - current_rank: str
      - current_level: int
      - current_xp: int
      - next_rank: str or None
      - next_threshold: int or None
      - xp_to_next: int or None
      - progress_percentage: int (0 to 100)
      - is_max_rank: bool
    """
    total_xp = get_user_total_xp(user)
    
    current_rank_info = RANKS[0]
    next_rank_info = None

    for i, rank in enumerate(RANKS):
        if total_xp >= rank['min_xp']:
            if rank['max_xp'] is None or total_xp <= rank['max_xp']:
                current_rank_info = rank
                if i + 1 < len(RANKS):
                    next_rank_info = RANKS[i + 1]
                else:
                    next_rank_info = None
                break

    if next_rank_info:
        span = next_rank_info['min_xp'] - current_rank_info['min_xp']
        progress_in_tier = total_xp - current_rank_info['min_xp']
        progress_pct = int(min(100, max(0, (progress_in_tier / span) * 100))) if span > 0 else 0
        xp_to_next = max(0, next_rank_info['min_xp'] - total_xp)
        next_rank_name = next_rank_info['name']
        next_threshold = next_rank_info['min_xp']
        is_max = False
    else:
        progress_pct = 100
        xp_to_next = 0
        next_rank_name = None
        next_threshold = None
        is_max = True

    # If user has progressed past Recruit into Sentinel, Ranger, or Warden, record rank notification
    if current_rank_info['level'] > 1:
        try:
            from notifications.services import create_notification
            from notifications.models import Notification
            create_notification(
                user=user,
                notification_type=Notification.TYPE_RANK_ACHIEVED,
                title="Rank Promotion",
                message=f'You have risen through the cold to the rank of {current_rank_info["name"]} (Tier {current_rank_info["level"]}).',
                dedup_key=f"rank_achieved_{user.pk}_{current_rank_info['name']}",
                source_type='rank',
                source_id=current_rank_info['name']
            )
        except Exception:
            pass

    return {
        'current_rank': current_rank_info['name'],
        'current_level': current_rank_info['level'],
        'current_xp': total_xp,
        'next_rank': next_rank_name,
        'next_threshold': next_threshold,
        'xp_to_next': xp_to_next,
        'progress_percentage': progress_pct,
        'is_max_rank': is_max,
    }

# Seeded Achievements (deterministic unlock criteria)
ACHIEVEMENT_DEFINITIONS = [
    {
        'code': 'FIRST_TASK',
        'name': 'The First Step',
        'description': 'Completed your first task of the crucible.',
        'xp_reward': 50,
    },
    {
        'code': 'FIRST_GOAL',
        'name': 'Oathkeeper',
        'description': 'Successfully completed an overarching strategic goal.',
        'xp_reward': 100,
    },
    {
        'code': 'STREAK_7',
        'name': 'The 7-Day Flame',
        'description': 'Maintained a 7-day habit streak through the cold.',
        'xp_reward': 150,
    },
    {
        'code': 'STREAK_30',
        'name': 'Iron Will',
        'description': 'Unbroken 30-day streak of relentless habit execution.',
        'xp_reward': 300,
    },
    {
        'code': 'FIRST_ARC',
        'name': 'Season Complete',
        'description': 'Completed an entire Winter Arc transformation period.',
        'xp_reward': 500,
    },
]

def check_and_unlock_achievements(user):
    """
    Evaluate deterministic criteria from actual user data and unlock eligible achievements.
    Awards XP reward if newly unlocked.
    Returns list of newly unlocked UserAchievement instances.
    """
    from tasks.models import Task
    from goals.models import Goal
    from habits.models import Habit
    from arcs.models import Arc

    # Ensure system achievements exist
    for d in ACHIEVEMENT_DEFINITIONS:
        Achievement.objects.get_or_create(
            code=d['code'],
            defaults={
                'name': d['name'],
                'description': d['description'],
                'xp_reward': d['xp_reward'],
            }
        )

    unlocked_list = []

    # Check FIRST_TASK
    if Task.objects.filter(user=user, status='COMPLETED').exists():
        _unlock(user, 'FIRST_TASK', unlocked_list)

    # Check FIRST_GOAL
    if Goal.objects.filter(user=user, status='COMPLETED').exists():
        _unlock(user, 'FIRST_GOAL', unlocked_list)

    # Check habit streaks (7d & 30d)
    user_habits = Habit.objects.filter(user=user)
    max_streak = max([h.best_streak for h in user_habits], default=0)
    if max_streak >= 7:
        _unlock(user, 'STREAK_7', unlocked_list)
    if max_streak >= 30:
        _unlock(user, 'STREAK_30', unlocked_list)

    # Check FIRST_ARC
    if Arc.objects.filter(user=user, status='COMPLETED').exists():
        _unlock(user, 'FIRST_ARC', unlocked_list)

    return unlocked_list

def _unlock(user, code, collector):
    try:
        achievement = Achievement.objects.get(code=code)
    except Achievement.DoesNotExist:
        return
    ua, created = UserAchievement.objects.get_or_create(user=user, achievement=achievement)
    if created:
        collector.append(ua)
        if achievement.xp_reward > 0:
            award_xp(
                user=user,
                source_type='achievement',
                source_id=f"ach_{achievement.code}",
                amount=achievement.xp_reward,
                description=f"Achievement unlocked: {achievement.name}"
            )
        try:
            from notifications.services import create_notification
            from notifications.models import Notification
            create_notification(
                user=user,
                notification_type=Notification.TYPE_ACHIEVEMENT_UNLOCKED,
                title="Crucible Badge Unlocked",
                message=f'You have forged the "{achievement.name}" badge! (+{achievement.xp_reward} XP)',
                dedup_key=f"ach_unlocked_{user.pk}_{achievement.code}",
                source_type='achievement',
                source_id=achievement.code
            )
        except Exception:
            pass
