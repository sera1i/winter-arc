from django.urls import path
from core import seo_views

urlpatterns = [
    # Primary Pillar & Cluster Pages
    path('winter-arc/', seo_views.pillar_view, name='winter_arc_pillar'),
    path('winter-arc/rules/', seo_views.rules_view, name='winter_arc_rules'),
    path('winter-arc/habits/', seo_views.habits_view, name='winter_arc_habits'),
    path('winter-arc/challenge/', seo_views.challenge_view, name='winter_arc_challenge'),
    path('winter-arc/templates/', seo_views.templates_view, name='winter_arc_templates'),
    path('winter-arc/for-students/', seo_views.for_students_view, name='winter_arc_for_students'),
    path('winter-arc/for-fitness/', seo_views.for_fitness_view, name='winter_arc_for_fitness'),
    path('winter-arc/for-career/', seo_views.for_career_view, name='winter_arc_for_career'),

    # Guides Cluster Pages
    path('guides/', seo_views.guides_index_view, name='guides_index'),
    path('guides/how-to-start-a-winter-arc/', seo_views.guide_how_to_start_view, name='guide_how_to_start'),
    path('guides/how-to-build-winter-arc-habits/', seo_views.guide_build_habits_view, name='guide_build_habits'),
    path('guides/winter-arc-daily-routine/', seo_views.guide_daily_routine_view, name='guide_daily_routine'),
    path('guides/winter-arc-goals/', seo_views.guide_goals_view, name='guide_goals'),
]
