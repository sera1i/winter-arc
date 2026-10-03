from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser, Profile
from arcs.models import Arc
from goals.models import Goal, Milestone

class GoalTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='goaltest', password='password123')
        self.other_user = CustomUser.objects.create_user(username='other', password='password123')
        Profile.objects.get_or_create(user=self.user)
        self.client.login(username='goaltest', password='password123')
        
        self.arc = Arc.objects.create(
            user=self.user,
            name="Test Arc",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=1),
            status='ACTIVE'
        )

        self.goal = Goal.objects.create(
            user=self.user,
            arc=self.arc,
            title="Initial Goal",
            status='IN_PROGRESS'
        )

    def test_goal_create(self):
        response = self.client.post(reverse('goals:create', args=[self.arc.pk]), {
            'title': 'New Goal',
            'description': 'Desc',
            'category': 'HEALTH',
            'priority': 1,
            'status': 'PENDING'
        })
        self.assertEqual(Goal.objects.count(), 2)
        new_goal = Goal.objects.get(title='New Goal')
        self.assertRedirects(response, reverse('arcs:detail', args=[self.arc.pk]))
        self.assertEqual(new_goal.user, self.user)

    def test_goal_detail_and_progress(self):
        # Add milestones
        m1 = Milestone.objects.create(goal=self.goal, title="M1")
        m2 = Milestone.objects.create(goal=self.goal, title="M2")
        
        # 0 completed
        self.assertEqual(self.goal.progress_percentage, 0)
        
        # Complete m1
        self.client.post(reverse('goals:milestone_toggle', args=[m1.pk]))
        self.assertEqual(self.goal.progress_percentage, 50)
        
        response = self.client.get(reverse('goals:detail', args=[self.goal.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '50<span class="text-xl text-slate-400">%</span>', html=True)

    def test_milestone_create_and_delete(self):
        response = self.client.post(reverse('goals:milestone_create', args=[self.goal.pk]), {
            'title': 'New Milestone'
        })
        self.assertEqual(self.goal.milestones.count(), 1)
        m = self.goal.milestones.first()
        self.assertRedirects(response, reverse('goals:detail', args=[self.goal.pk]))
        
        # Delete
        self.client.post(reverse('goals:milestone_delete', args=[m.pk]))
        self.assertEqual(self.goal.milestones.count(), 0)

    def test_milestone_update(self):
        m = Milestone.objects.create(goal=self.goal, title="Original Milestone")
        response = self.client.post(reverse('goals:milestone_update', args=[m.pk]), {
            'title': 'Renamed Milestone'
        })
        self.assertRedirects(response, reverse('goals:detail', args=[self.goal.pk]))
        m.refresh_from_db()
        self.assertEqual(m.title, 'Renamed Milestone')

    def test_goal_delete_hard_delete(self):
        goal_pk = self.goal.pk
        response = self.client.post(reverse('goals:delete', args=[goal_pk]), {'action': 'delete'})
        self.assertRedirects(response, reverse('arcs:detail', args=[self.arc.pk]))
        self.assertFalse(Goal.objects.filter(pk=goal_pk).exists())

    def test_goal_archive(self):
        response = self.client.post(reverse('goals:delete', args=[self.goal.pk]), {'action': 'archive'})
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.status, 'CANCELLED')

    def test_ownership_security(self):
        m = Milestone.objects.create(goal=self.goal, title="Owner Milestone")
        self.client.login(username='other', password='password123')
        
        # Access detail
        response = self.client.get(reverse('goals:detail', args=[self.goal.pk]))
        self.assertEqual(response.status_code, 404)
        
        # Edit
        response = self.client.post(reverse('goals:update', args=[self.goal.pk]), {'title': 'Hack'})
        self.assertEqual(response.status_code, 404)
        
        # Add milestone
        response = self.client.post(reverse('goals:milestone_create', args=[self.goal.pk]), {'title': 'Hack'})
        self.assertEqual(response.status_code, 404)

        # Milestone edit by other
        response = self.client.post(reverse('goals:milestone_update', args=[m.pk]), {'title': 'Hack Milestone'})
        self.assertEqual(response.status_code, 404)

        # Milestone delete by other
        response = self.client.post(reverse('goals:milestone_delete', args=[m.pk]))
        self.assertEqual(response.status_code, 404)

        # Milestone toggle by other
        response = self.client.post(reverse('goals:milestone_toggle', args=[m.pk]))
        self.assertEqual(response.status_code, 404)

