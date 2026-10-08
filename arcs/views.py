from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
import json

from .models import Arc
from .forms import ArcForm
from core.presets import get_all_presets, get_preset_by_key
from .preset_services import (
    initialize_blueprint_draft,
    validate_blueprint_draft,
    activate_blueprint_arc,
    parse_date_str,
)

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
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': True, 'arc_id': arc.pk, 'is_primary': True, 'status': arc.status})
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
    return redirect('arcs:detail', pk=arc.pk)


@login_required
def arc_pause(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    if request.method == 'POST':
        arc.status = 'PAUSED'
        arc.save()
        messages.success(request, f'Winter Arc "{arc.name}" paused.')
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': True, 'arc_id': arc.pk, 'status': arc.status})
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
    return redirect('arcs:detail', pk=arc.pk)


@login_required
def arc_resume(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    if request.method == 'POST':
        arc.status = 'ACTIVE'
        arc.save()
        messages.success(request, f'Winter Arc "{arc.name}" resumed.')
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': True, 'arc_id': arc.pk, 'status': arc.status})
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
    return redirect('arcs:detail', pk=arc.pk)


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
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': True, 'arc_id': arc.pk, 'status': arc.status})
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
    return redirect('arcs:detail', pk=arc.pk)


# ==============================================================================
# PRESET BLUEPRINT VIEWS
# ==============================================================================

@login_required
def preset_library(request):
    """Preset library starting point selection."""
    presets = get_all_presets()
    return render(request, 'arcs/preset_library.html', {
        'presets': presets,
    })


@login_required
def preset_review(request, key):
    """Review blueprint before entering customization."""
    preset = get_preset_by_key(key)
    if not preset:
        messages.error(request, f'Blueprint preset "{key}" not found.')
        return redirect('arcs:presets')

    session_key = f'preset_draft_{key}'
    existing_draft = request.session.get(session_key)
    if not existing_draft or (preset.key != 'custom' and preset.goal_count > 0 and len(existing_draft.get('goals', [])) == 0 and not existing_draft.get('is_user_customized')):
        request.session[session_key] = initialize_blueprint_draft(preset, request.user)
        request.session.modified = True

    return render(request, 'arcs/preset_review.html', {
        'preset': preset,
    })


@login_required
def preset_customize(request, key):
    """Customize blueprint parameters, goals, milestones, tasks, and habits."""
    preset = get_preset_by_key(key)
    if not preset:
        messages.error(request, f'Blueprint preset "{key}" not found.')
        return redirect('arcs:presets')

    session_key = f'preset_draft_{key}'
    errors = {}

    if request.method == 'POST':
        raw_payload = request.POST.get('customized_payload')
        draft_data = None
        if raw_payload:
            try:
                parsed = json.loads(raw_payload)
                if isinstance(parsed, str):
                    parsed = json.loads(parsed)
                if isinstance(parsed, dict):
                    draft_data = parsed
            except Exception:
                draft_data = None

        if not draft_data:
            # Fallback if raw_payload was missing or empty:
            # Preserve existing draft from session or preset defaults instead of wiping out goals/habits
            existing = request.session.get(session_key)
            if not existing or (preset.key != 'custom' and preset.goal_count > 0 and not existing.get('goals')):
                existing = initialize_blueprint_draft(preset, request.user)

            draft_data = {
                'name': request.POST.get('name') or existing.get('name', preset.name),
                'objective': request.POST.get('objective') or existing.get('objective', preset.objective),
                'start_date': request.POST.get('start_date') or existing.get('start_date'),
                'end_date': request.POST.get('end_date') or existing.get('end_date'),
                'timezone': request.POST.get('timezone') or existing.get('timezone', 'Asia/Kolkata'),
                'is_primary': request.POST.get('is_primary') in ('on', 'true', True),
                'goals': existing.get('goals', []),
                'habits': existing.get('habits', []),
            }

        draft_data['preset_key'] = key
        draft_data['preset_name'] = preset.name

        is_valid, cleaned_data, errors = validate_blueprint_draft(draft_data)
        if is_valid:
            cleaned_serializable = dict(cleaned_data)
            cleaned_serializable['start_date'] = cleaned_data['start_date'].isoformat()
            cleaned_serializable['end_date'] = cleaned_data['end_date'].isoformat()
            cleaned_serializable['is_user_customized'] = True
            request.session[session_key] = cleaned_serializable
            request.session.modified = True
            return redirect('arcs:preset_oath', key=key)
        else:
            draft = draft_data
    else:
        is_reset = request.GET.get('reset') == '1'
        existing_draft = request.session.get(session_key)

        needs_init = (
            is_reset or
            not existing_draft or
            (preset.key != 'custom' and preset.goal_count > 0 and len(existing_draft.get('goals', [])) == 0 and not existing_draft.get('is_user_customized'))
        )

        if needs_init:
            draft = initialize_blueprint_draft(preset, request.user)
            request.session[session_key] = draft
            request.session.modified = True
        else:
            draft = existing_draft

    return render(request, 'arcs/preset_customize.html', {
        'preset': preset,
        'draft': draft,
        'draft_json': json.dumps(draft),
        'errors': errors,
    })


@login_required
def preset_oath(request, key):
    """The Oath confirmation screen before activation."""
    preset = get_preset_by_key(key)
    if not preset:
        messages.error(request, f'Blueprint preset "{key}" not found.')
        return redirect('arcs:presets')

    session_key = f'preset_draft_{key}'
    existing_draft = request.session.get(session_key)
    if not existing_draft or (preset.key != 'custom' and preset.goal_count > 0 and len(existing_draft.get('goals', [])) == 0 and not existing_draft.get('is_user_customized')):
        draft = initialize_blueprint_draft(preset, request.user)
        request.session[session_key] = draft
        request.session.modified = True
    else:
        draft = existing_draft

    start_d = parse_date_str(draft.get('start_date'))
    end_d = parse_date_str(draft.get('end_date'))
    duration_days = (end_d - start_d).days if (start_d and end_d) else 90

    return render(request, 'arcs/preset_oath.html', {
        'preset': preset,
        'draft': draft,
        'start_date_obj': start_d,
        'end_date_obj': end_d,
        'duration_days': duration_days,
    })


@login_required
@require_POST
def preset_activate(request, key):
    """Atomically activate Arc and all child entities from session draft."""
    preset = get_preset_by_key(key)
    if not preset:
        messages.error(request, f'Blueprint preset "{key}" not found.')
        return redirect('arcs:presets')

    session_key = f'preset_draft_{key}'
    if session_key not in request.session:
        messages.error(request, 'No active blueprint draft found. Please review and customize your Arc.')
        return redirect('arcs:preset_customize', key=key)

    draft = request.session[session_key]
    is_valid, cleaned_data, errors = validate_blueprint_draft(draft)
    if not is_valid:
        messages.error(request, 'Blueprint configuration is incomplete or contains errors.')
        return redirect('arcs:preset_customize', key=key)

    arc = activate_blueprint_arc(request.user, cleaned_data)

    request.session.pop(session_key, None)
    request.session.modified = True

    messages.success(request, f'Winter Arc "{arc.name}" sworn and activated. Your watch begins now.')
    return redirect('arcs:detail', pk=arc.pk)


