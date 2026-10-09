from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from arcs.models import Arc
from .models import Goal, Milestone
from .forms import GoalForm, MilestoneForm

@login_required
def goal_create(request, arc_id):
    arc = get_object_or_404(Arc, pk=arc_id, user=request.user)
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.arc = arc
            goal.save()
            from analytics.services import log_activity
            log_activity(
                user=request.user,
                event_type='GOAL_CREATED',
                title=goal.title,
                arc=arc,
                source_type='goal',
                source_id=goal.pk
            )
            messages.success(request, 'Goal created successfully!')
            return redirect('arcs:detail', pk=arc.pk)
    else:
        form = GoalForm()
    return render(request, 'goals/goal_form.html', {'form': form, 'arc': arc, 'title': 'Create New Goal'})

@login_required
def goal_detail(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    milestone_form = MilestoneForm()
    return render(request, 'goals/goal_detail.html', {
        'goal': goal,
        'milestones': goal.milestones.all().order_by('due_date', 'created_at'),
        'milestone_form': milestone_form
    })

@login_required
def goal_update(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Goal updated successfully!')
            return redirect('goals:detail', pk=goal.pk)
    else:
        form = GoalForm(instance=goal)
    return render(request, 'goals/goal_form.html', {'form': form, 'arc': goal.arc, 'title': 'Edit Goal'})

@login_required
def goal_delete(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    arc_pk = goal.arc.pk if goal.arc else None
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'archive':
            goal.status = 'CANCELLED'
            goal.save()
            messages.success(request, f'Goal "{goal.title}" archived.')
        else:
            goal_title = goal.title
            goal.delete()
            messages.success(request, f'Goal "{goal_title}" permanently deleted.')
        if arc_pk:
            return redirect('arcs:detail', pk=arc_pk)
        return redirect('accounts:dashboard')
    return render(request, 'goals/goal_confirm_delete.html', {'goal': goal})

@login_required
def milestone_create(request, goal_id):
    goal = get_object_or_404(Goal, pk=goal_id, user=request.user)
    if request.method == 'POST':
        form = MilestoneForm(request.POST)
        if form.is_valid():
            milestone = form.save(commit=False)
            milestone.goal = goal
            milestone.save()
            messages.success(request, 'Milestone added!')
    return redirect('goals:detail', pk=goal.pk)

@login_required
def milestone_update(request, pk):
    milestone = get_object_or_404(Milestone, pk=pk, goal__user=request.user)
    if request.method == 'POST':
        form = MilestoneForm(request.POST, instance=milestone)
        if form.is_valid():
            form.save()
            messages.success(request, f'Milestone "{milestone.title}" updated.')
            return redirect('goals:detail', pk=milestone.goal.pk)
    else:
        form = MilestoneForm(instance=milestone)
    return render(request, 'goals/milestone_form.html', {
        'form': form,
        'milestone': milestone,
        'goal': milestone.goal,
        'title': 'Edit Milestone Checkpoint',
    })

@login_required
def milestone_toggle(request, pk):
    milestone = get_object_or_404(Milestone.objects.select_related('goal', 'goal__arc'), pk=pk, goal__user=request.user)
    if request.method == 'POST':
        from django.db import transaction
        with transaction.atomic():
            if milestone.completed_at:
                milestone.completed_at = None
            else:
                milestone.completed_at = timezone.now()
                from gamification.services import award_xp, check_and_unlock_achievements
                from analytics.services import log_activity
                
                arc = milestone.goal.arc if milestone.goal else None
                award_xp(
                    user=request.user,
                    source_type='milestone',
                    source_id=milestone.pk,
                    description=f'Completed milestone: {milestone.title}',
                    arc=arc
                )
                log_activity(
                    user=request.user,
                    event_type='MILESTONE_COMPLETED',
                    title=f'Checkpoint reached: {milestone.title}',
                    arc=arc,
                    source_type='milestone',
                    source_id=milestone.pk
                )
                
                # Check if this completed the parent goal
                milestones = list(milestone.goal.milestones.all())
                all_done = all(m.is_completed or m.pk == milestone.pk for m in milestones)
                if all_done and milestone.goal.status != 'COMPLETED':
                    milestone.goal.status = 'COMPLETED'
                    milestone.goal.save(update_fields=['status', 'updated_at'])
                    award_xp(
                        user=request.user,
                        source_type='goal',
                        source_id=milestone.goal.pk,
                        description=f'Completed goal: {milestone.goal.title}',
                        arc=arc
                    )
                    log_activity(
                        user=request.user,
                        event_type='GOAL_COMPLETED',
                        title=f'Oath fulfilled: {milestone.goal.title}',
                        arc=arc,
                        source_type='goal',
                        source_id=milestone.goal.pk
                    )

                check_and_unlock_achievements(request.user, trigger_type='milestone')

            milestone.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'success': True,
                'milestone_id': milestone.pk,
                'is_completed': milestone.is_completed,
                'goal_id': milestone.goal.pk,
                'goal_progress': milestone.goal.progress_percentage,
                'goal_status': milestone.goal.status,
            })
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
    return redirect('goals:detail', pk=milestone.goal.pk)

@login_required
def goal_complete(request, pk):
    goal = get_object_or_404(Goal.objects.select_related('arc'), pk=pk, user=request.user)
    if request.method == 'POST':
        from django.db import transaction
        with transaction.atomic():
            was_completed = (goal.status == 'COMPLETED')
            if not was_completed:
                goal.status = 'COMPLETED'
                goal.save(update_fields=['status', 'updated_at'])
                from gamification.services import award_xp, check_and_unlock_achievements
                from analytics.services import log_activity

                arc = goal.arc if goal.arc else None
                award_xp(
                    user=request.user,
                    source_type='goal',
                    source_id=goal.pk,
                    description=f'Completed goal: {goal.title}',
                    arc=arc
                )
                log_activity(
                    user=request.user,
                    event_type='GOAL_COMPLETED',
                    title=f'Oath fulfilled: {goal.title}',
                    arc=arc,
                    source_type='goal',
                    source_id=goal.pk
                )
                check_and_unlock_achievements(request.user, trigger_type='goal')
                messages.success(request, f'Goal "{goal.title}" fulfilled.')
            else:
                goal.status = 'IN_PROGRESS' if goal.milestones.exists() else 'PENDING'
                goal.save(update_fields=['status', 'updated_at'])
                messages.info(request, f'Goal "{goal.title}" reopened.')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'success': True,
                'goal_id': goal.pk,
                'status': goal.status,
                'is_completed': goal.status == 'COMPLETED',
                'progress_percentage': goal.progress_percentage,
                'message': f'Goal "{goal.title}" {"fulfilled" if goal.status == "COMPLETED" else "reopened"}.',
            })

        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
        if goal.arc:
            return redirect('arcs:detail', pk=goal.arc.pk)
        return redirect('dashboard')
    return redirect('goals:detail', pk=pk)

@login_required
def milestone_delete(request, pk):
    milestone = get_object_or_404(Milestone, pk=pk, goal__user=request.user)
    goal_pk = milestone.goal.pk
    if request.method == 'POST':
        milestone.delete()
        messages.success(request, 'Milestone removed.')
        return redirect('goals:detail', pk=goal_pk)
    return redirect('goals:detail', pk=goal_pk)
