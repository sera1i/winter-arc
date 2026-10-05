from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q

from accounts.models import Profile
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from journal.models import JournalEntry
from notifications.models import Notification, NotificationPreference
from gamification.models import XPEvent, Achievement, UserAchievement

from gamification.services import award_xp, check_and_unlock_achievements, get_user_total_xp, get_user_rank, RANKS
from analytics.services import log_activity
from analytics.progress_services import get_full_analytics_summary, get_task_statistics, get_habit_statistics, calculate_arc_progress

from .serializers import (
    UserMeSerializer,
    ProfileSerializer,
    ArcSerializer,
    GoalSerializer,
    MilestoneSerializer,
    TaskSerializer,
    HabitSerializer,
    HabitCompletionSerializer,
    JournalEntrySerializer,
    NotificationSerializer,
    NotificationPreferenceSerializer,
    AnalyticsSummarySerializer,
    GamificationSummarySerializer,
    PresetDefinitionSerializer,
)
from core.presets import get_all_presets, get_preset_by_key


# ---------------------------------------------------------------------------
# /me/ endpoint
# ---------------------------------------------------------------------------

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserMeSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Arc ViewSet
# ---------------------------------------------------------------------------

class ArcViewSet(viewsets.ModelViewSet):
    serializer_class = ArcSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'objective']
    ordering_fields = ['start_date', 'end_date', 'created_at', 'name']
    ordering = ['-is_primary', '-created_at']

    def get_queryset(self):
        qs = Arc.objects.filter(user=self.request.user)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        return qs

    def perform_create(self, serializer):
        arc = serializer.save(user=self.request.user)
        log_activity(
            user=self.request.user,
            event_type='ARC_CREATED',
            title=arc.name,
            arc=arc,
            source_type='arc',
            source_id=arc.pk
        )

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        arc = self.get_object()
        Arc.objects.filter(user=request.user, is_primary=True).exclude(pk=arc.pk).update(is_primary=False)
        arc.is_primary = True
        arc.save(update_fields=['is_primary', 'updated_at'])
        return Response(ArcSerializer(arc).data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        arc = self.get_object()
        arc.status = 'ARCHIVED'
        arc.is_primary = False
        arc.save(update_fields=['status', 'is_primary', 'updated_at'])
        return Response(ArcSerializer(arc).data)


# ---------------------------------------------------------------------------
# Goal ViewSet
# ---------------------------------------------------------------------------

class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'category']
    ordering_fields = ['priority', 'deadline', 'created_at', 'title']
    ordering = ['priority', '-created_at']

    def get_queryset(self):
        qs = Goal.objects.filter(user=self.request.user).prefetch_related('milestones')
        arc_param = self.request.query_params.get('arc')
        if arc_param:
            qs = qs.filter(arc_id=arc_param)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        goal = self.get_object()
        was_completed = goal.status == 'COMPLETED'
        goal.status = 'COMPLETED'
        goal.save(update_fields=['status', 'updated_at'])

        if not was_completed:
            award_xp(
                user=request.user,
                source_type='goal',
                source_id=goal.pk,
                description=f'Completed goal: {goal.title}',
                arc=goal.arc
            )
            log_activity(
                user=request.user,
                event_type='GOAL_COMPLETED',
                title=f'Goal Achieved: {goal.title}',
                arc=goal.arc,
                source_type='goal',
                source_id=goal.pk
            )
            check_and_unlock_achievements(request.user)

        return Response(GoalSerializer(goal).data)


# ---------------------------------------------------------------------------
# Milestone ViewSet
# ---------------------------------------------------------------------------

class MilestoneViewSet(viewsets.ModelViewSet):
    serializer_class = MilestoneSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['due_date', 'created_at', 'title']
    ordering = ['due_date', 'created_at']

    def get_queryset(self):
        qs = Milestone.objects.filter(goal__user=self.request.user).select_related('goal')
        goal_param = self.request.query_params.get('goal')
        if goal_param:
            qs = qs.filter(goal_id=goal_param)
        return qs

    def perform_create(self, serializer):
        # validate_goal already verified ownership
        serializer.save()

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        milestone = self.get_object()
        was_completed = milestone.is_completed
        if not was_completed:
            milestone.completed_at = timezone.now()
            milestone.save(update_fields=['completed_at', 'updated_at'])
            award_xp(
                user=request.user,
                source_type='milestone',
                source_id=milestone.pk,
                description=f'Completed milestone: {milestone.title}',
                arc=milestone.goal.arc if milestone.goal else None
            )
            log_activity(
                user=request.user,
                event_type='MILESTONE_COMPLETED',
                title=f'Milestone reached: {milestone.title}',
                arc=milestone.goal.arc if milestone.goal else None,
                source_type='milestone',
                source_id=milestone.pk
            )
            check_and_unlock_achievements(request.user)

        return Response(MilestoneSerializer(milestone).data)


# ---------------------------------------------------------------------------
# Task ViewSet
# ---------------------------------------------------------------------------

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['priority', 'due_at', 'created_at', 'title']
    ordering = ['priority', 'due_at', '-created_at']

    def get_queryset(self):
        qs = Task.objects.filter(user=self.request.user).select_related('goal')
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        goal_param = self.request.query_params.get('goal')
        if goal_param:
            qs = qs.filter(goal_id=goal_param)
        arc_param = self.request.query_params.get('arc')
        if arc_param:
            qs = qs.filter(goal__arc_id=arc_param)
        return qs

    def perform_create(self, serializer):
        task = serializer.save(user=self.request.user)
        arc = task.goal.arc if task.goal else None
        log_activity(
            user=self.request.user,
            event_type='TASK_CREATED',
            title=task.title,
            arc=arc,
            source_type='task',
            source_id=task.pk
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        was_completed = task.is_completed
        task.complete()

        arc = task.goal.arc if task.goal else None
        award_xp(
            user=request.user,
            source_type='task',
            source_id=task.pk,
            description=f'Completed task: {task.title}',
            arc=arc
        )
        if not was_completed:
            log_activity(
                user=request.user,
                event_type='TASK_COMPLETED',
                title=f'Completed: {task.title}',
                arc=arc,
                source_type='task',
                source_id=task.pk
            )
            check_and_unlock_achievements(request.user)

        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def uncomplete(self, request, pk=None):
        task = self.get_object()
        task.uncomplete()
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        task = self.get_object()
        task.status = 'CANCELLED'
        task.save(update_fields=['status', 'updated_at'])
        return Response(TaskSerializer(task).data)


# ---------------------------------------------------------------------------
# Habit ViewSet
# ---------------------------------------------------------------------------

class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        qs = Habit.objects.filter(user=self.request.user).prefetch_related('completions')
        archived = self.request.query_params.get('archived')
        if archived is not None:
            is_archived = archived.lower() in ['true', '1']
            qs = qs.filter(is_archived=is_archived)
        return qs

    def perform_create(self, serializer):
        habit = serializer.save(user=self.request.user)
        log_activity(
            user=self.request.user,
            event_type='HABIT_CREATED',
            title=habit.name,
            source_type='habit',
            source_id=habit.pk
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        habit = self.get_object()
        today = habit.get_user_today()
        completion, created = HabitCompletion.objects.get_or_create(
            habit=habit, local_date=today
        )
        if created:
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

        return Response({
            "status": "completed",
            "habit": HabitSerializer(habit).data,
            "completion": HabitCompletionSerializer(completion).data
        })

    @action(detail=True, methods=['post'])
    def undo(self, request, pk=None):
        habit = self.get_object()
        today = habit.get_user_today()
        HabitCompletion.objects.filter(habit=habit, local_date=today).delete()
        return Response({
            "status": "undone",
            "habit": HabitSerializer(habit).data
        })

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        habit = self.get_object()
        habit.is_archived = True
        habit.save(update_fields=['is_archived', 'updated_at'])
        return Response(HabitSerializer(habit).data)


# ---------------------------------------------------------------------------
# Journal ViewSet
# ---------------------------------------------------------------------------

class JournalViewSet(viewsets.ModelViewSet):
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['local_date', 'created_at']
    ordering = ['-local_date']

    def get_queryset(self):
        return JournalEntry.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        entry = serializer.save(user=self.request.user)
        award_xp(
            user=self.request.user,
            source_type='journal',
            source_id=f"{entry.pk}_{entry.local_date}",
            description=f'Journal reflection for {entry.local_date}'
        )
        log_activity(
            user=self.request.user,
            event_type='JOURNAL_ENTRY',
            title=f'Reflected: {entry.local_date}',
            source_type='journal',
            source_id=entry.pk
        )
        check_and_unlock_achievements(self.request.user)


# ---------------------------------------------------------------------------
# Notification ViewSet & Preferences
# ---------------------------------------------------------------------------

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        is_read_param = self.request.query_params.get('is_read')
        if is_read_param is not None:
            is_read = is_read_param.lower() in ['true', '1']
            qs = qs.filter(is_read=is_read)
        return qs

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        now = timezone.now()
        updated_count = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=now
        )
        return Response({'marked_read': updated_count})


class NotificationPreferenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs)
        return Response(serializer.data)

    def patch(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Read-Only Analytics & Gamification Views
# ---------------------------------------------------------------------------

class AnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        arc_id = request.query_params.get('arc_id')
        summary = get_full_analytics_summary(request.user, arc_id=arc_id)
        
        # Format for clean JSON output
        serialized_events = [
            {
                'id': ev.id,
                'event_type': ev.event_type,
                'title': ev.title,
                'created_at': ev.created_at.isoformat(),
                'arc_id': ev.arc_id,
            }
            for ev in summary['recent_events']
        ]

        data = {
            'arc_progress': summary['arc_progress'],
            'task_stats': summary['task_stats'],
            'habit_stats': summary['habit_stats'],
            'rank_info': summary['rank_info'],
            'activity_7d': summary['activity_7d'],
            'activity_30d': summary['activity_30d'],
            'recent_events': serialized_events,
        }
        return Response(data)


class GamificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        total_xp = get_user_total_xp(request.user)
        rank_info = get_user_rank(request.user)
        
        # User achievements
        user_achievements = {
            ua.achievement_id: ua.unlocked_at
            for ua in UserAchievement.objects.filter(user=request.user)
        }
        all_achievements = Achievement.objects.all()
        achievements_data = []
        for ach in all_achievements:
            unlocked = ach.id in user_achievements
            achievements_data.append({
                'code': ach.code,
                'name': ach.name,
                'description': ach.description,
                'xp_reward': ach.xp_reward,
                'criteria_version': ach.criteria_version,
                'is_unlocked': unlocked,
                'unlocked_at': user_achievements[ach.id].isoformat() if unlocked else None,
            })

        # Recent XP events
        recent_xp = XPEvent.objects.filter(user=request.user).order_by('-created_at')[:10]
        xp_events_data = [
            {
                'id': xp.id,
                'source_type': xp.source_type,
                'source_id': xp.source_id,
                'amount': xp.amount,
                'description': xp.description,
                'created_at': xp.created_at.isoformat(),
            }
            for xp in recent_xp
        ]

        return Response({
            'total_xp': total_xp,
            'current_rank': rank_info,
            'achievements': achievements_data,
            'recent_xp_events': xp_events_data,
        })


# ---------------------------------------------------------------------------
# Presets (Read-Only Blueprints)
# ---------------------------------------------------------------------------

class PresetListView(APIView):
    """
    Expose available Winter Arc starting presets/blueprints.
    Read-only endpoint. Presets are customizable templates, not official rules.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        presets = get_all_presets()
        serializer = PresetDefinitionSerializer([p.to_dict() for p in presets], many=True)
        return Response(serializer.data)


class PresetDetailView(APIView):
    """
    Expose a single Winter Arc preset/blueprint by its slug key.
    Read-only endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, key):
        preset = get_preset_by_key(key)
        if not preset:
            return Response(
                {'detail': f'Preset "{key}" not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = PresetDefinitionSerializer(preset.to_dict())
        return Response(serializer.data)

