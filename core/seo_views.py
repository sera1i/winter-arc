from django.shortcuts import render
from django.conf import settings
from core.presets import get_all_presets


def _get_seo_context(request, title, description, canonical_path, og_type="article"):
    site_url = getattr(settings, 'SITE_URL', 'https://arcinwinter.up.railway.app').rstrip('/')
    canonical_url = f"{site_url}{canonical_path}"
    return {
        'SITE_URL': site_url,
        'page_title': title,
        'meta_description': description,
        'canonical_url': canonical_url,
        'canonical_path': canonical_path,
        'og_type': og_type,
    }


def pillar_view(request):
    """Primary Pillar Page: /winter-arc/"""
    ctx = _get_seo_context(
        request,
        title="What Is a Winter Arc? A Practical Guide to the Winter Arc Challenge",
        description="Learn what a Winter Arc is, how the 90-day self-improvement challenge works, why people do it, and how to structure your goals, daily habits, and routines.",
        canonical_path="/winter-arc/",
        og_type="article"
    )
    return render(request, 'seo/pillar.html', ctx)


def rules_view(request):
    """Supporting Page: /winter-arc/rules/"""
    ctx = _get_seo_context(
        request,
        title="Winter Arc Rules — How to Set Measurable Daily Standards",
        description="Discover how to set effective, measurable Winter Arc rules. Learn the difference between vague ambitions and actionable daily standards, with realistic examples.",
        canonical_path="/winter-arc/rules/",
        og_type="article"
    )
    return render(request, 'seo/rules.html', ctx)


def habits_view(request):
    """Supporting Page: /winter-arc/habits/"""
    ctx = _get_seo_context(
        request,
        title="Winter Arc Habit Ideas — 30+ Measurable Habits for Mind, Body & Work",
        description="Explore 30+ practical, measurable Winter Arc habit ideas organized by Physical, Mental, Study, Career, Digital Discipline, and Sleep. Build your daily system.",
        canonical_path="/winter-arc/habits/",
        og_type="article"
    )
    return render(request, 'seo/habits.html', ctx)


def challenge_view(request):
    """Supporting Page: /winter-arc/challenge/"""
    ctx = _get_seo_context(
        request,
        title="The Winter Arc Challenge — 90 Days of Unapologetic Focus",
        description="Understand the Winter Arc Challenge: why participants use the 90 days before the new year to build focus, how it works, and how to stay consistent across the season.",
        canonical_path="/winter-arc/challenge/",
        og_type="article"
    )
    return render(request, 'seo/challenge.html', ctx)


def templates_view(request):
    """Supporting Page: /winter-arc/templates/"""
    presets = get_all_presets()
    ctx = _get_seo_context(
        request,
        title="Winter Arc Templates & Starting Blueprints",
        description="Explore ready-to-use Winter Arc templates and customizable blueprints. From Student Lock-In to Fitness Arc, Monk Mode, and Mind + Body, find your starting point.",
        canonical_path="/winter-arc/templates/",
        og_type="website"
    )
    ctx['presets'] = presets
    return render(request, 'seo/templates.html', ctx)


def for_students_view(request):
    """Supporting Page: /winter-arc/for-students/"""
    ctx = _get_seo_context(
        request,
        title="Winter Arc for Students — Academic Lock-In, Exam Prep & Focus",
        description="How to structure a Winter Arc as a student. Balance high GPA study sessions, exam revision, sleep hygiene, and physical health without burning out.",
        canonical_path="/winter-arc/for-students/",
        og_type="article"
    )
    return render(request, 'seo/for_students.html', ctx)


def for_fitness_view(request):
    """Supporting Page: /winter-arc/for-fitness/"""
    ctx = _get_seo_context(
        request,
        title="Winter Arc for Fitness — Training, Nutrition & Physical Mastery",
        description="Build an uncompromising physical foundation with a fitness-focused Winter Arc. Learn sustainable strength routines, nutrition consistency, and recovery habits.",
        canonical_path="/winter-arc/for-fitness/",
        og_type="article"
    )
    return render(request, 'seo/for_fitness.html', ctx)


def for_career_view(request):
    """Supporting Page: /winter-arc/for-career/"""
    ctx = _get_seo_context(
        request,
        title="Winter Arc for Career — Deep Work, Upskilling & Professional Momentum",
        description="Level up your career with a 90-day Winter Arc. Structure deep work blocks, ship portfolio projects, master new technical skills, and achieve professional breakthroughs.",
        canonical_path="/winter-arc/for-career/",
        og_type="article"
    )
    return render(request, 'seo/for_career.html', ctx)


def guides_index_view(request):
    """Guides Hub: /guides/"""
    ctx = _get_seo_context(
        request,
        title="Winter Arc Field Guides — Discipline, Habits & Goal Systems",
        description="Comprehensive, practical guides for planning, launching, and executing a successful Winter Arc. Actionable frameworks for habits, routines, goals, and daily systems.",
        canonical_path="/guides/",
        og_type="website"
    )
    return render(request, 'seo/guides_index.html', ctx)


def guide_how_to_start_view(request):
    """Guide: /guides/how-to-start-a-winter-arc/"""
    ctx = _get_seo_context(
        request,
        title="How to Start a Winter Arc — A 10-Step Guide to Complete Transformation",
        description="A comprehensive 10-step roadmap to launch your Winter Arc. Learn how to choose your dates, set 3–5 core goals, engineer daily habits, and track your season.",
        canonical_path="/guides/how-to-start-a-winter-arc/",
        og_type="article"
    )
    return render(request, 'seo/guide_how_to_start.html', ctx)


def guide_build_habits_view(request):
    """Guide: /guides/how-to-build-winter-arc-habits/"""
    ctx = _get_seo_context(
        request,
        title="How to Build Winter Arc Habits — The Behavioral Engineering Framework",
        description="Learn the behavioral engineering loop for Winter Arc habits: Goal → Behavior → Frequency → Measurement → Tracking → Review. Build habits that last.",
        canonical_path="/guides/how-to-build-winter-arc-habits/",
        og_type="article"
    )
    return render(request, 'seo/guide_build_habits.html', ctx)


def guide_daily_routine_view(request):
    """Guide: /guides/winter-arc-daily-routine/"""
    ctx = _get_seo_context(
        request,
        title="The Winter Arc Daily Routine — Realistic Schedules for Students & Professionals",
        description="Explore realistic Winter Arc daily routines tailored for students, 9-to-5 professionals, and fitness enthusiasts. Build a sustainable daily rhythm.",
        canonical_path="/guides/winter-arc-daily-routine/",
        og_type="article"
    )
    return render(request, 'seo/guide_daily_routine.html', ctx)


def guide_goals_view(request):
    """Guide: /guides/winter-arc-goals/"""
    ctx = _get_seo_context(
        request,
        title="Mastering Winter Arc Goals — From Long-Term Vision to Daily Execution",
        description="Learn how to structure Winter Arc goals using a systematic hierarchy: Arc → Goals → Milestones → Tasks & Habits. Turn broad ambitions into daily progress.",
        canonical_path="/guides/winter-arc-goals/",
        og_type="article"
    )
    return render(request, 'seo/guide_goals.html', ctx)
