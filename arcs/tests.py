from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser, Profile
from arcs.models import Arc

class ArcTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='arctest', password='password123')
        Profile.objects.get_or_create(user=self.user)
        self.client.login(username='arctest', password='password123')
        
        self.today = timezone.now().date()
        self.tomorrow = self.today + timedelta(days=1)
        
        self.arc = Arc.objects.create(
            user=self.user,
            name="Initial Arc",
            objective="Initial objective",
            start_date=self.today,
            end_date=self.tomorrow,
            status='ACTIVE'
        )

    def test_arc_list_view(self):
        response = self.client.get(reverse('arcs:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Initial Arc")

    def test_arc_create(self):
        response = self.client.post(reverse('arcs:create'), {
            'name': 'New Arc',
            'objective': 'New objective',
            'start_date': self.today,
            'end_date': self.tomorrow,
            'status': 'DRAFT',
            'timezone': 'UTC'
        })
        self.assertEqual(Arc.objects.count(), 2)
        new_arc = Arc.objects.get(name='New Arc')
        self.assertRedirects(response, reverse('arcs:detail', args=[new_arc.pk]))

    def test_arc_create_invalid_dates(self):
        response = self.client.post(reverse('arcs:create'), {
            'name': 'Bad Arc',
            'objective': 'Bad objective',
            'start_date': self.tomorrow,
            'end_date': self.today, # End date before start date
            'status': 'DRAFT',
            'timezone': 'UTC'
        })
        self.assertEqual(response.status_code, 200) # Form renders with errors
        self.assertContains(response, "Start date cannot be after end date")
        self.assertEqual(Arc.objects.count(), 1) # Only initial arc

    def test_arc_update(self):
        response = self.client.post(reverse('arcs:update', args=[self.arc.pk]), {
            'name': 'Updated Arc',
            'objective': 'Updated objective',
            'start_date': self.today,
            'end_date': self.tomorrow,
            'status': 'ACTIVE',
            'timezone': 'UTC'
        })
        self.arc.refresh_from_db()
        self.assertEqual(self.arc.name, 'Updated Arc')
        self.assertRedirects(response, reverse('arcs:detail', args=[self.arc.pk]))

    def test_arc_archive(self):
        response = self.client.post(reverse('arcs:delete', args=[self.arc.pk]))
        self.arc.refresh_from_db()
        self.assertEqual(self.arc.status, 'ARCHIVED')
        self.assertRedirects(response, reverse('arcs:list'))

    def test_arc_make_primary(self):
        # Create second active arc
        arc2 = Arc.objects.create(
            user=self.user, name="Arc 2", objective="Obj", 
            start_date=self.today, end_date=self.tomorrow, status='ACTIVE'
        )
        # Make Arc 2 primary
        response = self.client.post(reverse('arcs:make_primary', args=[arc2.pk]))
        arc2.refresh_from_db()
        self.assertTrue(arc2.is_primary)
        
        # Now make initial arc primary
        response = self.client.post(reverse('arcs:make_primary', args=[self.arc.pk]))
        self.arc.refresh_from_db()
        arc2.refresh_from_db()
        
        self.assertTrue(self.arc.is_primary)
        self.assertFalse(arc2.is_primary) # Ensured unique primary arc

    def test_arc_pause_resume_complete(self):
        # Pause
        r = self.client.post(reverse('arcs:pause', args=[self.arc.pk]))
        self.arc.refresh_from_db()
        self.assertEqual(self.arc.status, 'PAUSED')

        # Resume
        r = self.client.post(reverse('arcs:resume', args=[self.arc.pk]))
        self.arc.refresh_from_db()
        self.assertEqual(self.arc.status, 'ACTIVE')

        # Complete
        r = self.client.post(reverse('arcs:complete', args=[self.arc.pk]))
        self.arc.refresh_from_db()
        self.assertEqual(self.arc.status, 'COMPLETED')
        self.assertFalse(self.arc.is_primary)

    def test_arc_permanent_delete(self):
        r = self.client.post(reverse('arcs:delete', args=[self.arc.pk]), {'action': 'delete'})
        self.assertRedirects(r, reverse('arcs:list'))
        self.assertFalse(Arc.objects.filter(pk=self.arc.pk).exists())


class ArcSecurityTests(TestCase):
    def setUp(self):
        self.user_a = CustomUser.objects.create_user(username='usera', password='password123')
        self.user_b = CustomUser.objects.create_user(username='userb', password='password123')
        Profile.objects.get_or_create(user=self.user_a)
        Profile.objects.get_or_create(user=self.user_b)
        self.client.login(username='userb', password='password123')

        self.arc_a = Arc.objects.create(
            user=self.user_a,
            name="User A Private Arc",
            objective="Secret",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            status='ACTIVE'
        )

    def test_cannot_view_other_user_arc(self):
        r = self.client.get(reverse('arcs:detail', args=[self.arc_a.pk]))
        self.assertEqual(r.status_code, 404)

    def test_cannot_edit_other_user_arc(self):
        r = self.client.post(reverse('arcs:update', args=[self.arc_a.pk]), {'name': 'Tampered'})
        self.assertEqual(r.status_code, 404)

    def test_cannot_delete_other_user_arc(self):
        r = self.client.post(reverse('arcs:delete', args=[self.arc_a.pk]), {'action': 'delete'})
        self.assertEqual(r.status_code, 404)

    def test_cannot_pause_or_resume_other_user_arc(self):
        r = self.client.post(reverse('arcs:pause', args=[self.arc_a.pk]))
        self.assertEqual(r.status_code, 404)
        r = self.client.post(reverse('arcs:resume', args=[self.arc_a.pk]))
        self.assertEqual(r.status_code, 404)

