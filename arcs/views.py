from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Arc
from .forms import ArcForm

@login_required
def arc_list(request):
    arcs = request.user.arcs.all().order_by('-is_primary', '-created_at')
    return render(request, 'arcs/arc_list.html', {'arcs': arcs})

@login_required
def arc_detail(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    goals = arc.goals.all().prefetch_related('milestones')
    return render(request, 'arcs/arc_detail.html', {'arc': arc, 'goals': goals})

@login_required
def arc_create(request):
    if request.method == 'POST':
        arc_instance = Arc(user=request.user)
        form = ArcForm(request.POST, instance=arc_instance)
        if form.is_valid():
            arc = form.save(commit=False)
            arc.user = request.user
            arc.save()
            from analytics.services import log_activity
            log_activity(
                user=request.user,
                event_type='ARC_STARTED',
                title=f'Sworn: {arc.name}',
                arc=arc,
                source_type='arc',
                source_id=arc.pk
            )
            messages.success(request, 'Winter Arc created successfully!')
            return redirect('arcs:detail', pk=arc.pk)
    else:
        initial = {'timezone': 'UTC'}
        if hasattr(request.user, 'profile'):
            initial['timezone'] = request.user.profile.timezone
        form = ArcForm(initial=initial)
    return render(request, 'arcs/arc_form.html', {'form': form, 'title': 'Create Winter Arc'})

@login_required
def arc_update(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ArcForm(request.POST, instance=arc)
        if form.is_valid():
            form.save()
            messages.success(request, 'Winter Arc updated successfully!')
            return redirect('arcs:detail', pk=arc.pk)
    else:
        form = ArcForm(instance=arc)
    return render(request, 'arcs/arc_form.html', {'form': form, 'title': 'Edit Winter Arc'})

@login_required
def arc_delete(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    if request.method == 'POST':
        action = request.POST.get('action', 'archive')
        if action == 'delete':
            arc_name = arc.name
            arc.delete()
            messages.success(request, f'Winter Arc "{arc_name}" permanently deleted.')
        else:
            arc.status = 'ARCHIVED'
            arc.is_primary = False
            arc.save()
            messages.success(request, f'Winter Arc "{arc.name}" archived successfully.')
        return redirect('arcs:list')
    return render(request, 'arcs/arc_confirm_delete.html', {'arc': arc})

@login_required
def arc_make_primary(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    if request.method == 'POST':
        request.user.arcs.filter(is_primary=True).update(is_primary=False)
        arc.is_primary = True
        arc.save()
        messages.success(request, f'"{arc.name}" is now your primary Arc.')
    return redirect(request.META.get('HTTP_REFERER') or 'arcs:list')


@login_required
def arc_pause(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    if request.method == 'POST':
        arc.status = 'PAUSED'
        arc.save()
        messages.success(request, f'Winter Arc "{arc.name}" paused.')
    return redirect(request.META.get('HTTP_REFERER') or 'arcs:detail', pk=arc.pk)


@login_required
def arc_resume(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    if request.method == 'POST':
        arc.status = 'ACTIVE'
        arc.save()
        messages.success(request, f'Winter Arc "{arc.name}" resumed.')
    return redirect(request.META.get('HTTP_REFERER') or 'arcs:detail', pk=arc.pk)


@login_required
def arc_complete(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    if request.method == 'POST':
        arc.status = 'COMPLETED'
        arc.is_primary = False
        arc.save()
        from gamification.services import award_xp, check_and_unlock_achievements
        from analytics.services import log_activity
        
        award_xp(
            user=request.user,
            source_type='arc',
            source_id=arc.pk,
            description=f'Completed Winter Arc: {arc.name}',
            arc=arc
        )
        log_activity(
            user=request.user,
            event_type='ARC_COMPLETED',
            title=f'Crucible Concluded: {arc.name}',
            arc=arc,
            source_type='arc',
            source_id=arc.pk
        )
        check_and_unlock_achievements(request.user)
        messages.success(request, f'Winter Arc "{arc.name}" marked as completed. Well done.')
    return redirect(request.META.get('HTTP_REFERER') or 'arcs:detail', pk=arc.pk)

