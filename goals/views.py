from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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
    milestone = get_object_or_404(Milestone, pk=pk, goal__user=request.user)
    if request.method == 'POST':
        if milestone.completed_at:
            milestone.completed_at = None
        else:
            milestone.completed_at = timezone.now()
        milestone.save()
    return redirect('goals:detail', pk=milestone.goal.pk)

@login_required
def milestone_delete(request, pk):
    milestone = get_object_or_404(Milestone, pk=pk, goal__user=request.user)
    goal_pk = milestone.goal.pk
    if request.method == 'POST':
        milestone.delete()
        messages.success(request, 'Milestone removed.')
        return redirect('goals:detail', pk=goal_pk)
    return redirect('goals:detail', pk=goal_pk)
