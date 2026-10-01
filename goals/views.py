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
    arc_pk = goal.arc.pk
    if request.method == 'POST':
        goal.status = 'CANCELLED' # Archive instead of hard delete
        goal.save()
        messages.success(request, 'Goal cancelled/archived.')
        return redirect('arcs:detail', pk=arc_pk)
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
def milestone_toggle(request, pk):
    if request.method == 'POST':
        # Need to join Goal to check ownership securely
        milestone = get_object_or_404(Milestone, pk=pk, goal__user=request.user)
        if milestone.completed_at:
            milestone.completed_at = None
        else:
            milestone.completed_at = timezone.now()
        milestone.save()
    return redirect('goals:detail', pk=milestone.goal.pk)

@login_required
def milestone_delete(request, pk):
    if request.method == 'POST':
        milestone = get_object_or_404(Milestone, pk=pk, goal__user=request.user)
        goal_pk = milestone.goal.pk
        milestone.delete()
        messages.success(request, 'Milestone removed.')
        return redirect('goals:detail', pk=goal_pk)
    return redirect('goals:detail', pk=pk) # Fallback if GET
