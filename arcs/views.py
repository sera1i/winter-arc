from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Arc
from .forms import ArcForm

@login_required
def arc_list(request):
    arcs = request.user.arcs.all().order_by('-created_at')
    return render(request, 'arcs/arc_list.html', {'arcs': arcs})

@login_required
def arc_detail(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    return render(request, 'arcs/arc_detail.html', {'arc': arc})

@login_required
def arc_create(request):
    if request.method == 'POST':
        form = ArcForm(request.POST)
        if form.is_valid():
            arc = form.save(commit=False)
            arc.user = request.user
            try:
                arc.full_clean()
                arc.save()
                messages.success(request, 'Winter Arc created successfully!')
                return redirect('arcs:detail', pk=arc.pk)
            except ValidationError as e:
                for field, errs in e.message_dict.items():
                    for err in errs:
                        form.add_error(field if field != '__all__' else None, err)
    else:
        # Default timezone from profile if available
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
            try:
                form.instance.full_clean()
                form.save()
                messages.success(request, 'Winter Arc updated successfully!')
                return redirect('arcs:detail', pk=arc.pk)
            except ValidationError as e:
                for field, errs in e.message_dict.items():
                    for err in errs:
                        form.add_error(field if field != '__all__' else None, err)
    else:
        form = ArcForm(instance=arc)
    return render(request, 'arcs/arc_form.html', {'form': form, 'title': 'Edit Winter Arc'})

@login_required
def arc_delete(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    if request.method == 'POST':
        # Explicit confirmation check could be done via POST parameters if needed
        # WA-ARC-014: "should prefer archival where historical data is valuable"
        arc.status = 'ARCHIVED'
        arc.save()
        messages.success(request, 'Winter Arc archived successfully.')
        return redirect('arcs:list')
    return render(request, 'arcs/arc_confirm_delete.html', {'arc': arc})

@login_required
def arc_make_primary(request, pk):
    arc = get_object_or_404(Arc, pk=pk, user=request.user)
    if request.method == 'POST':
        # Unmark existing primary arcs
        request.user.arcs.filter(is_primary=True).update(is_primary=False)
        arc.is_primary = True
        arc.save()
        messages.success(request, f'{arc.name} is now your primary Arc.')
    return redirect('arcs:list')
