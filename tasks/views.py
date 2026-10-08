from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import Task
from .forms import TaskForm


@login_required
def task_list(request):
    status_filter = request.GET.get('status', '')
    tasks = Task.objects.filter(user=request.user).select_related('goal').exclude(status='CANCELLED')
    if status_filter:
        tasks = tasks.filter(status=status_filter)

    context = {
        'tasks': tasks,
        'status_filter': status_filter,
        'pending_count': Task.objects.filter(user=request.user, status='PENDING').count(),
        'inprogress_count': Task.objects.filter(user=request.user, status='IN_PROGRESS').count(),
        'completed_count': Task.objects.filter(user=request.user, status='COMPLETED').count(),
    }
    return render(request, 'tasks/task_list.html', context)


@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            # Guard: ensure goal belongs to this user
            if task.goal and task.goal.user != request.user:
                task.goal = None
            task.save()
            from analytics.services import log_activity
            arc = task.goal.arc if task.goal else None
            log_activity(
                user=request.user,
                event_type='TASK_CREATED',
                title=task.title,
                arc=arc,
                source_type='task',
                source_id=task.pk
            )
            messages.success(request, f'Task "{task.title}" created.')
            return redirect('tasks:detail', pk=task.pk)
    else:
        form = TaskForm(user=request.user)
    return render(request, 'tasks/task_form.html', {'form': form, 'title': 'Create Task'})


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    return render(request, 'tasks/task_detail.html', {'task': task})


@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.goal and updated.goal.user != request.user:
                updated.goal = None
            updated.save()
            messages.success(request, 'Task updated.')
            return redirect('tasks:detail', pk=task.pk)
    else:
        form = TaskForm(instance=task, user=request.user)
    return render(request, 'tasks/task_form.html', {'form': form, 'task': task, 'title': 'Edit Task'})


@login_required
def task_complete(request, pk):
    if request.method == 'POST':
        task = get_object_or_404(Task, pk=pk, user=request.user)
        was_completed = task.is_completed
        task.complete()
        
        from gamification.services import award_xp, check_and_unlock_achievements
        from analytics.services import log_activity

        arc = task.goal.arc if task.goal else None
        event, created = award_xp(
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

        messages.success(request, 'Done. The frost gives way.')
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'success': True,
                'task_id': task.pk,
                'status': task.status,
                'is_completed': task.is_completed,
                'message': 'Done. The frost gives way.',
            })
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
        return redirect('tasks:detail', pk=pk)
    return redirect('tasks:detail', pk=pk)


@login_required
def task_uncomplete(request, pk):
    if request.method == 'POST':
        task = get_object_or_404(Task, pk=pk, user=request.user)
        task.uncomplete()
        messages.success(request, f'"{task.title}" marked incomplete.')
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'success': True,
                'task_id': task.pk,
                'status': task.status,
                'is_completed': task.is_completed,
                'message': f'"{task.title}" marked incomplete.',
            })
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
        return redirect('tasks:detail', pk=pk)
    return redirect('tasks:detail', pk=pk)


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'cancel':
            task.status = 'CANCELLED'
            task.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'Task "{task.title}" cancelled.')
        else:
            task_title = task.title
            task.delete()
            messages.success(request, f'Task "{task_title}" permanently deleted.')
        return redirect('tasks:list')
    return render(request, 'tasks/task_confirm_delete.html', {'task': task})

