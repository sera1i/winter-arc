from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from zoneinfo import ZoneInfo
from .models import JournalEntry
from .forms import JournalEntryForm
from gamification.services import award_xp, check_and_unlock_achievements
from analytics.services import log_activity


def _get_user_today(user):
    """Return today's date in the user's configured timezone."""
    try:
        from django.conf import settings
        tz_name = getattr(user.profile, 'timezone', None) if (user and hasattr(user, 'profile')) else None
        if not tz_name:
            tz_name = getattr(settings, 'TIME_ZONE', 'Asia/Kolkata')
        user_tz = ZoneInfo(tz_name)
    except Exception:
        user_tz = timezone.get_current_timezone()
    return timezone.now().astimezone(user_tz).date()


@login_required
def journal_list(request):
    entries = JournalEntry.objects.filter(user=request.user).order_by('-local_date', '-created_at')
    today = _get_user_today(request.user)
    has_today_entry = entries.filter(local_date=today).exists()
    today_entry = entries.filter(local_date=today).first() if has_today_entry else None

    context = {
        'entries': entries,
        'today': today,
        'has_today_entry': has_today_entry,
        'today_entry': today_entry,
        'total_entries': entries.count(),
    }
    return render(request, 'journal/journal_list.html', context)


@login_required
def journal_detail(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    return render(request, 'journal/journal_detail.html', {'entry': entry})


@login_required
def journal_create(request):
    today = _get_user_today(request.user)
    
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, user=request.user)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()

            # Award XP idempotently (40 XP)
            award_xp(
                user=request.user,
                source_type='journal',
                source_id=f"{entry.pk}_{entry.local_date}",
                description=f'Journal reflection for {entry.local_date}'
            )
            # Log Activity idempotently
            log_activity(
                user=request.user,
                event_type='JOURNAL_ENTRY',
                title=f'Reflected: {entry.local_date}',
                source_type='journal',
                source_id=entry.pk
            )
            check_and_unlock_achievements(request.user)

            messages.success(request, f'Journal entry for {entry.local_date} recorded. Reflection saved (+40 XP).')
            return redirect('journal:detail', pk=entry.pk)
    else:
        # Prepopulate with today's local date
        form = JournalEntryForm(initial={'local_date': today}, user=request.user)

    return render(request, 'journal/journal_form.html', {
        'form': form,
        'title': 'New Journal Entry',
        'is_edit': False,
    })


@login_required
def journal_update(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)

    if request.method == 'POST':
        form = JournalEntryForm(request.POST, instance=entry, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Journal entry for {entry.local_date} updated.')
            return redirect('journal:detail', pk=entry.pk)
    else:
        form = JournalEntryForm(instance=entry, user=request.user)

    return render(request, 'journal/journal_form.html', {
        'form': form,
        'entry': entry,
        'title': f'Edit Journal Entry — {entry.local_date}',
        'is_edit': True,
    })


@login_required
def journal_delete(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)

    if request.method == 'POST':
        date_str = str(entry.local_date)
        entry.delete()
        messages.success(request, f'Journal entry for {date_str} permanently deleted.')
        return redirect('journal:list')

    return render(request, 'journal/journal_confirm_delete.html', {'entry': entry})
