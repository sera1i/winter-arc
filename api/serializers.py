from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.models import Profile
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from journal.models import JournalEntry
from notifications.models import Notification, NotificationPreference
from gamification.models import XPEvent, Achievement, UserAchievement

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['display_name', 'avatar', 'timezone', 'bio', 'preferences']


class UserMeSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'profile']
        read_only_fields = ['id', 'username', 'email', 'date_joined', 'profile']


# ---------------------------------------------------------------------------
# Arcs
# ---------------------------------------------------------------------------

class ArcSerializer(serializers.ModelSerializer):
    class Meta:
        model = Arc
        fields = [
            'id', 'name', 'objective', 'start_date', 'end_date',
            'status', 'is_primary', 'timezone', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        start_date = data.get('start_date') or (self.instance.start_date if self.instance else None)
        end_date = data.get('end_date') or (self.instance.end_date if self.instance else None)
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({"end_date": "End date cannot be earlier than start date."})
        return data


# ---------------------------------------------------------------------------
# Goals & Milestones
# ---------------------------------------------------------------------------

class MilestoneSerializer(serializers.ModelSerializer):
    is_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Milestone
        fields = [
            'id', 'goal', 'title', 'target_value', 'due_date',
            'completed_at', 'is_completed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'completed_at', 'is_completed', 'created_at', 'updated_at']

    def validate_goal(self, goal):
        request = self.context.get('request')
        if request and goal.user != request.user:
            raise serializers.ValidationError("Cannot link milestone to a goal belonging to another user.")
        return goal


class GoalSerializer(serializers.ModelSerializer):
    milestones = MilestoneSerializer(many=True, read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = Goal
        fields = [
            'id', 'arc', 'title', 'description', 'category', 'priority',
            'target_value', 'current_value', 'unit', 'deadline',
            'status', 'progress_percentage', 'milestones', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'progress_percentage', 'milestones', 'created_at', 'updated_at']

    def validate_arc(self, arc):
        if arc is not None:
            request = self.context.get('request')
            if request and arc.user != request.user:
                raise serializers.ValidationError("Cannot assign goal to an Arc belonging to another user.")
        return arc


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class TaskSerializer(serializers.ModelSerializer):
    is_completed = serializers.BooleanField(read_only=True)
    priority_label = serializers.CharField(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'goal', 'title', 'description', 'due_at', 'priority',
            'priority_label', 'status', 'recurrence_rule', 'completed_at',
            'is_completed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'completed_at', 'is_completed', 'priority_label', 'created_at', 'updated_at']

    def validate_goal(self, goal):
        if goal is not None:
            request = self.context.get('request')
            if request and goal.user != request.user:
                raise serializers.ValidationError("Cannot assign task to a goal belonging to another user.")
        return goal


# ---------------------------------------------------------------------------
# Habits & Completions
# ---------------------------------------------------------------------------

class HabitCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitCompletion
        fields = ['id', 'habit', 'local_date', 'quantity', 'completed_at']
        read_only_fields = ['id', 'completed_at']


class HabitSerializer(serializers.ModelSerializer):
    current_streak = serializers.SerializerMethodField()
    best_streak = serializers.ReadOnlyField()
    is_completed_today = serializers.SerializerMethodField()

    class Meta:
        model = Habit
        fields = [
            'id', 'name', 'description', 'frequency', 'target_count',
            'active_from', 'active_until', 'is_archived', 'current_streak',
            'best_streak', 'is_completed_today', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_streak', 'best_streak', 'is_completed_today', 'created_at', 'updated_at']

    def get_current_streak(self, obj):
        return obj.get_current_streak()

    def get_is_completed_today(self, obj):
        return obj.is_completed_today()


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------

class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = [
            'id', 'local_date', 'mood', 'energy', 'sleep_hours',
            'reflection', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_mood(self, value):
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError("Mood must be between 1 and 5.")
        return value

    def validate_energy(self, value):
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError("Energy must be between 1 and 5.")
        return value


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read',
            'created_at', 'read_at', 'source_type', 'source_id',
            'scheduled_for'
        ]
        read_only_fields = [
            'id', 'notification_type', 'title', 'message', 'created_at',
            'read_at', 'source_type', 'source_id', 'scheduled_for'
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'push_enabled', 'quiet_start', 'quiet_end',
            'task_reminders_enabled', 'habit_reminders_enabled',
            'deadline_reminders_enabled', 'gamification_alerts_enabled',
            'updated_at'
        ]
        read_only_fields = ['updated_at']


# ---------------------------------------------------------------------------
# Analytics & Gamification (Read-Only)
# ---------------------------------------------------------------------------

class GamificationSummarySerializer(serializers.Serializer):
    total_xp = serializers.IntegerField()
    current_rank = serializers.DictField()
    achievements = serializers.ListField()
    recent_xp_events = serializers.ListField()


class AnalyticsSummarySerializer(serializers.Serializer):
    arc_progress = serializers.IntegerField()
    task_stats = serializers.DictField()
    habit_stats = serializers.DictField()
    rank_info = serializers.DictField()
    activity_7d = serializers.DictField()
    activity_30d = serializers.DictField()
    recent_events = serializers.ListField()


# ---------------------------------------------------------------------------
# Presets (Read-Only Blueprints)
# ---------------------------------------------------------------------------

class MilestoneBlueprintSerializer(serializers.Serializer):
    title = serializers.CharField()
    target_value = serializers.FloatField(required=False, allow_null=True)
    days_offset = serializers.IntegerField(required=False, allow_null=True)


class TaskBlueprintSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.IntegerField(default=2)
    days_offset = serializers.IntegerField(required=False, allow_null=True)


class GoalBlueprintSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField()
    priority = serializers.IntegerField()
    milestones = MilestoneBlueprintSerializer(many=True)
    tasks = TaskBlueprintSerializer(many=True)


class HabitBlueprintSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    frequency = serializers.CharField()
    target_count = serializers.IntegerField()
    target_label = serializers.CharField()


class PresetDefinitionSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    tagline = serializers.CharField()
    description = serializers.CharField()
    objective = serializers.CharField()
    recommended_duration_days = serializers.IntegerField()
    goal_count = serializers.IntegerField()
    habit_count = serializers.IntegerField()
    goals = GoalBlueprintSerializer(many=True)
    habits = HabitBlueprintSerializer(many=True)

