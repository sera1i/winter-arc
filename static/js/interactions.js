/**
 * Winter Arc — Interaction Performance & Action Navigation Engine
 * 
 * Provides:
 * 1. Immediate visual click feedback (optimistic / loading states)
 * 2. In-place completion for Tasks, Habits, Milestones, Goals, Notifications
 * 3. Prevention of duplicate requests / double submission
 * 4. Isolation of action controls (stopping event propagation to parent cards)
 * 5. Accessible loading & error states
 * 6. Single-submission login protection with instant feedback
 */

(function () {
    'use strict';

    // -------------------------------------------------------------------------
    // CSRF Utility
    // -------------------------------------------------------------------------
    function getCsrfToken() {
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input && input.value) return input.value;
        const cookieMatch = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return cookieMatch ? decodeURIComponent(cookieMatch[1]) : '';
    }

    // -------------------------------------------------------------------------
    // Toast Notification System (Non-disruptive Error & Status Alerts)
    // -------------------------------------------------------------------------
    function showToast(message, type) {
        type = type || 'error';
        let container = document.getElementById('wa-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'wa-toast-container';
            container.className = 'wa-toast-container';
            container.setAttribute('aria-live', 'polite');
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = 'wa-toast ' + (type === 'error' ? 'wa-toast-error' : 'bg-steel/20 border border-steel/60 text-bone');
        toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(function () {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(6px)';
            setTimeout(function () {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }

    // -------------------------------------------------------------------------
    // Task Complete / Uncomplete Handler
    // -------------------------------------------------------------------------
    function handleTaskForm(form, button) {
        if (button.hasAttribute('disabled') || button.dataset.loading === 'true') {
            return;
        }

        const actionUrl = form.getAttribute('action');
        if (!actionUrl) return;

        const tStart = performance.now();
        const indicator = button.querySelector('.wa-checkbox-indicator') || button;
        const wasCompleted = indicator.classList.contains('is-completed') || actionUrl.includes('/uncomplete/');
        const willBeCompleted = !wasCompleted;
        const csrfToken = getCsrfToken();

        // Find parent row to update text style
        const taskRow = form.closest('.task-row') || form.closest('li') || form.closest('[data-task-id]');
        const titleLink = taskRow ? taskRow.querySelector('a[href*="/tasks/"]') : null;

        // TRUE OPTIMISTIC UI: apply visual state changes immediately (<5ms in same frame)
        button.dataset.loading = 'true';
        button.setAttribute('aria-busy', 'true');
        button.disabled = true;

        if (willBeCompleted) {
            indicator.classList.add('is-completed');
            indicator.textContent = '✓';
            indicator.classList.remove('text-transparent');
            indicator.classList.add('text-bone');
            button.setAttribute('title', 'Mark pending');
            button.setAttribute('aria-label', 'Undo completion');
            if (titleLink) {
                titleLink.classList.add('line-through', 'text-ice/50');
                titleLink.classList.remove('text-bone');
            }
        } else {
            indicator.classList.remove('is-completed');
            indicator.textContent = '✓';
            indicator.classList.add('text-transparent');
            indicator.classList.remove('text-bone');
            button.setAttribute('title', 'Mark complete');
            button.setAttribute('aria-label', 'Complete task');
            if (titleLink) {
                titleLink.classList.remove('line-through', 'text-ice/50');
                titleLink.classList.add('text-bone');
            }
        }

        const tOptimistic = performance.now();
        window.__wa_last_interaction = {
            type: willBeCompleted ? 'task_complete' : 'task_uncomplete',
            optimistic_ms: tOptimistic - tStart,
            completed: false
        };

        fetch(actionUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            body: new URLSearchParams(new FormData(form))
        })
        .then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function (data) {
            const tEnd = performance.now();
            if (window.__wa_last_interaction) {
                window.__wa_last_interaction.total_ms = tEnd - tStart;
                window.__wa_last_interaction.network_ms = tEnd - tOptimistic;
                window.__wa_last_interaction.completed = true;
            }

            button.dataset.loading = 'false';
            button.removeAttribute('aria-busy');
            button.disabled = false;

            const isNowCompleted = (typeof data.is_completed !== 'undefined') 
                ? data.is_completed 
                : (data.status === 'COMPLETED');

            // Switch action endpoint for next toggle
            if (isNowCompleted && actionUrl.includes('/complete/')) {
                form.setAttribute('action', actionUrl.replace('/complete/', '/uncomplete/'));
            } else if (!isNowCompleted && actionUrl.includes('/uncomplete/')) {
                form.setAttribute('action', actionUrl.replace('/uncomplete/', '/complete/'));
            }
        })
        .catch(function (err) {
            // Revert optimistic state on failure
            button.dataset.loading = 'false';
            button.removeAttribute('aria-busy');
            button.disabled = false;

            if (wasCompleted) {
                indicator.classList.add('is-completed');
                indicator.textContent = '✓';
                indicator.classList.remove('text-transparent');
                indicator.classList.add('text-bone');
                button.setAttribute('title', 'Mark pending');
                button.setAttribute('aria-label', 'Undo completion');
                if (titleLink) {
                    titleLink.classList.add('line-through', 'text-ice/50');
                    titleLink.classList.remove('text-bone');
                }
            } else {
                indicator.classList.remove('is-completed');
                indicator.textContent = '✓';
                indicator.classList.add('text-transparent');
                indicator.classList.remove('text-bone');
                button.setAttribute('title', 'Mark complete');
                button.setAttribute('aria-label', 'Complete task');
                if (titleLink) {
                    titleLink.classList.remove('line-through', 'text-ice/50');
                    titleLink.classList.add('text-bone');
                }
            }
            showToast('Could not update task. Please try again.');
        });
    }

    // -------------------------------------------------------------------------
    // Habit Complete / Undo Handler
    // -------------------------------------------------------------------------
    function handleHabitForm(form, button) {
        if (button.hasAttribute('disabled') || button.dataset.loading === 'true') {
            return;
        }

        const actionUrl = form.getAttribute('action');
        if (!actionUrl) return;

        const tStart = performance.now();
        const wasCompleted = button.classList.contains('wa-habit-btn-completed') || button.textContent.includes('Done');
        const willBeCompleted = !wasCompleted;
        const origClassName = button.className;
        const origText = button.textContent;
        const habitContainer = form.closest('li') || form.closest('.wa-card') || form.closest('[data-habit-id]');
        const streakEl = habitContainer ? habitContainer.querySelector('strong') : null;
        const origStreakText = streakEl ? streakEl.textContent : '';
        const csrfToken = getCsrfToken();

        // TRUE OPTIMISTIC UI: apply visual state changes immediately (<5ms in same frame)
        button.dataset.loading = 'true';
        button.setAttribute('aria-busy', 'true');
        button.disabled = true;

        if (willBeCompleted) {
            button.textContent = 'Done ✓';
            button.setAttribute('title', 'Click to undo completion');
            button.setAttribute('aria-label', 'Undo habit completion');
            button.className = button.className
                .replace('text-ice/60 border-steel/30', 'text-crimson-light border-crimson/50 bg-crimson/10')
                .replace('btn-primary', 'font-mono text-[10px] uppercase text-crimson-light border border-crimson/50 bg-crimson/10');
            button.classList.add('wa-habit-btn-completed');
            button.classList.remove('wa-habit-btn-pending');
            if (streakEl && origStreakText.includes('d')) {
                const count = parseInt(origStreakText.replace('d', ''), 10) || 0;
                streakEl.textContent = (count + 1) + 'd';
            }
        } else {
            button.textContent = 'Mark done';
            button.setAttribute('title', 'Mark done');
            button.setAttribute('aria-label', 'Complete habit');
            button.className = button.className
                .replace('text-crimson-light border-crimson/50 bg-crimson/10', 'text-ice/60 border-steel/30')
                .replace('text-crimson-light border border-crimson/50 bg-crimson/10', 'btn-primary');
            button.classList.add('wa-habit-btn-pending');
            button.classList.remove('wa-habit-btn-completed');
            if (streakEl && origStreakText.includes('d')) {
                const count = parseInt(origStreakText.replace('d', ''), 10) || 0;
                streakEl.textContent = Math.max(0, count - 1) + 'd';
            }
        }

        const tOptimistic = performance.now();
        window.__wa_last_interaction = {
            type: willBeCompleted ? 'habit_complete' : 'habit_undo',
            optimistic_ms: tOptimistic - tStart,
            completed: false
        };

        fetch(actionUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            body: new URLSearchParams(new FormData(form))
        })
        .then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function (data) {
            const tEnd = performance.now();
            if (window.__wa_last_interaction) {
                window.__wa_last_interaction.total_ms = tEnd - tStart;
                window.__wa_last_interaction.network_ms = tEnd - tOptimistic;
                window.__wa_last_interaction.completed = true;
            }

            button.dataset.loading = 'false';
            button.removeAttribute('aria-busy');
            button.disabled = false;

            // Sync authoritative server streak counter if present
            if (habitContainer && typeof data.streak !== 'undefined' && streakEl) {
                streakEl.textContent = data.streak + 'd';
            }
        })
        .catch(function (err) {
            // Revert optimistic state on failure
            button.className = origClassName;
            button.textContent = origText;
            if (streakEl) streakEl.textContent = origStreakText;
            button.dataset.loading = 'false';
            button.removeAttribute('aria-busy');
            button.disabled = false;
            showToast('Could not update habit. Please try again.');
        });
    }

    // -------------------------------------------------------------------------
    // Milestone Toggle Handler
    // -------------------------------------------------------------------------
    function handleMilestoneForm(form, button) {
        if (button.hasAttribute('disabled') || button.dataset.loading === 'true') {
            return;
        }

        const actionUrl = form.getAttribute('action');
        if (!actionUrl) return;

        const tStart = performance.now();
        const indicator = button.querySelector('.wa-checkbox-indicator') || button;
        const wasCompleted = indicator.classList.contains('is-completed');
        const willBeCompleted = !wasCompleted;
        const milestoneRow = form.closest('.task-row') || form.closest('li') || form.closest('div');
        const titleSpan = milestoneRow ? milestoneRow.querySelector('span.text-sm') : null;
        const csrfToken = getCsrfToken();

        // TRUE OPTIMISTIC UI: apply visual changes immediately
        button.dataset.loading = 'true';
        button.setAttribute('aria-busy', 'true');
        button.disabled = true;

        if (willBeCompleted) {
            indicator.classList.add('is-completed');
            indicator.textContent = '✓';
            indicator.classList.remove('text-transparent');
            indicator.classList.add('text-bone');
            if (titleSpan) {
                titleSpan.classList.add('line-through', 'text-ice/50');
                titleSpan.classList.remove('text-bone');
            }
        } else {
            indicator.classList.remove('is-completed');
            indicator.textContent = '✓';
            indicator.classList.add('text-transparent');
            indicator.classList.remove('text-bone');
            if (titleSpan) {
                titleSpan.classList.remove('line-through', 'text-ice/50');
                titleSpan.classList.add('text-bone');
            }
        }

        const tOptimistic = performance.now();
        window.__wa_last_interaction = {
            type: willBeCompleted ? 'milestone_complete' : 'milestone_undo',
            optimistic_ms: tOptimistic - tStart,
            completed: false
        };

        fetch(actionUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            body: new URLSearchParams(new FormData(form))
        })
        .then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function (data) {
            const tEnd = performance.now();
            if (window.__wa_last_interaction) {
                window.__wa_last_interaction.total_ms = tEnd - tStart;
                window.__wa_last_interaction.network_ms = tEnd - tOptimistic;
                window.__wa_last_interaction.completed = true;
            }

            button.dataset.loading = 'false';
            button.removeAttribute('aria-busy');
            button.disabled = false;

            // Update parent goal progress bar if present
            if (typeof data.goal_progress !== 'undefined') {
                const progressFill = document.querySelector('.progress-bar-fill');
                if (progressFill) {
                    progressFill.style.width = data.goal_progress + '%';
                }
                const progressText = document.querySelector('.font-serif.text-3xl.text-crimson');
                if (progressText) {
                    progressText.innerHTML = data.goal_progress + '<span class="text-xl text-slate-400">%</span>';
                }
            }
        })
        .catch(function (err) {
            button.dataset.loading = 'false';
            button.removeAttribute('aria-busy');
            button.disabled = false;

            if (wasCompleted) {
                indicator.classList.add('is-completed');
                indicator.textContent = '✓';
                indicator.classList.remove('text-transparent');
                indicator.classList.add('text-bone');
                if (titleSpan) {
                    titleSpan.classList.add('line-through', 'text-ice/50');
                    titleSpan.classList.remove('text-bone');
                }
            } else {
                indicator.classList.remove('is-completed');
                indicator.textContent = '✓';
                indicator.classList.add('text-transparent');
                indicator.classList.remove('text-bone');
                if (titleSpan) {
                    titleSpan.classList.remove('line-through', 'text-ice/50');
                    titleSpan.classList.add('text-bone');
                }
            }
            showToast('Could not update checkpoint. Please try again.');
        });
    }

    // -------------------------------------------------------------------------
    // Goal Complete Handler
    // -------------------------------------------------------------------------
    function handleGoalCompleteForm(form, button) {
        if (button.hasAttribute('disabled') || button.dataset.loading === 'true') {
            return;
        }

        const actionUrl = form.getAttribute('action');
        if (!actionUrl) return;

        const tStart = performance.now();
        const origText = button.textContent;
        const wasCompleted = origText.includes('Reopen');
        const willBeCompleted = !wasCompleted;
        const csrfToken = getCsrfToken();

        // TRUE OPTIMISTIC UI: apply visual state changes immediately
        button.dataset.loading = 'true';
        button.setAttribute('aria-busy', 'true');
        button.disabled = true;

        if (willBeCompleted) {
            button.textContent = 'Reopen Goal';
        } else {
            button.textContent = 'Fulfill Goal';
        }

        const tOptimistic = performance.now();
        window.__wa_last_interaction = {
            type: willBeCompleted ? 'goal_complete' : 'goal_reopen',
            optimistic_ms: tOptimistic - tStart,
            completed: false
        };

        fetch(actionUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            body: new URLSearchParams(new FormData(form))
        })
        .then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function (data) {
            const tEnd = performance.now();
            if (window.__wa_last_interaction) {
                window.__wa_last_interaction.total_ms = tEnd - tStart;
                window.__wa_last_interaction.network_ms = tEnd - tOptimistic;
                window.__wa_last_interaction.completed = true;
            }

            button.dataset.loading = 'false';
            button.removeAttribute('aria-busy');
            button.disabled = false;

            if (data.is_completed) {
                button.textContent = 'Reopen Goal';
            } else {
                button.textContent = 'Fulfill Goal';
            }
        })
        .catch(function (err) {
            button.textContent = origText;
            button.dataset.loading = 'false';
            button.removeAttribute('aria-busy');
            button.disabled = false;
            showToast('Could not update goal. Please try again.');
        });
    }

    // -------------------------------------------------------------------------
    // Notification Mark Read Handler
    // -------------------------------------------------------------------------
    function handleNotificationForm(form, button) {
        if (button.hasAttribute('disabled') || button.dataset.loading === 'true') {
            return;
        }

        const actionUrl = form.getAttribute('action');
        if (!actionUrl) return;

        button.dataset.loading = 'true';
        button.setAttribute('aria-busy', 'true');
        button.disabled = true;
        button.style.opacity = '0.5';
        const csrfToken = getCsrfToken();

        fetch(actionUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            body: new URLSearchParams(new FormData(form))
        })
        .then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function (data) {
            button.dataset.loading = 'false';
            button.removeAttribute('aria-busy');

            if (actionUrl.includes('/mark_all_read/')) {
                // All read
                document.querySelectorAll('.wa-card.border-l-4').forEach(function (card) {
                    card.classList.remove('border-l-4', 'border-l-crimson', 'bg-steel/10');
                    card.classList.add('opacity-75');
                });
                button.parentElement.innerHTML = '<span class="font-mono text-[10px] text-ice/40 tracking-wider uppercase">All Read</span>';
            } else {
                // Single read
                const card = form.closest('.wa-card');
                if (card) {
                    card.classList.remove('border-l-4', 'border-l-crimson', 'bg-steel/10');
                    card.classList.add('opacity-75');
                    const unreadDot = card.querySelector('.bg-crimson.rounded-full');
                    if (unreadDot) unreadDot.remove();
                }
                form.parentElement.innerHTML = '<span class="font-mono text-[10px] text-ice/40 tracking-wider uppercase">Read</span>';
            }

            // Update badge counts in page if any
            if (typeof data.unread_count !== 'undefined') {
                document.querySelectorAll('[data-notification-badge]').forEach(function (badge) {
                    if (data.unread_count === 0) {
                        badge.classList.add('hidden');
                    } else {
                        badge.textContent = data.unread_count;
                        badge.classList.remove('hidden');
                    }
                });
            }
        })
        .catch(function (err) {
            button.style.opacity = '';
            button.dataset.loading = 'false';
            button.removeAttribute('aria-busy');
            button.disabled = false;
            showToast('Could not update notification.');
        });
    }

    // -------------------------------------------------------------------------
    // Event Delegation: Intercept Action Forms & Prevent Card Navigation
    // -------------------------------------------------------------------------
    document.addEventListener('submit', function (e) {
        const form = e.target;
        if (!form || !form.action) return;

        const action = form.getAttribute('action') || '';

        // 1. Task actions
        if (action.includes('/tasks/') && (action.includes('/complete/') || action.includes('/uncomplete/'))) {
            e.preventDefault();
            e.stopPropagation();
            const btn = form.querySelector('button[type="submit"]') || form.querySelector('button');
            if (btn) handleTaskForm(form, btn);
            return;
        }

        // 2. Habit actions
        if (action.includes('/habits/') && action.includes('/complete/')) {
            e.preventDefault();
            e.stopPropagation();
            const btn = form.querySelector('button[type="submit"]') || form.querySelector('button');
            if (btn) handleHabitForm(form, btn);
            return;
        }

        // 3. Milestone toggle actions
        if (action.includes('/goals/milestones/') && action.includes('/toggle/')) {
            e.preventDefault();
            e.stopPropagation();
            const btn = form.querySelector('button[type="submit"]') || form.querySelector('button');
            if (btn) handleMilestoneForm(form, btn);
            return;
        }

        // 4. Goal complete actions
        if (action.includes('/goals/') && action.includes('/complete/')) {
            e.preventDefault();
            e.stopPropagation();
            const btn = form.querySelector('button[type="submit"]') || form.querySelector('button');
            if (btn) handleGoalCompleteForm(form, btn);
            return;
        }

        // 5. Notification mark read actions
        if (action.includes('/notifications/mark_read/') || action.includes('/notifications/mark_all_read/')) {
            e.preventDefault();
            e.stopPropagation();
            const btn = form.querySelector('button[type="submit"]') || form.querySelector('button');
            if (btn) handleNotificationForm(form, btn);
            return;
        }

        // 6. Login single submission protection
        if (action.includes('/accounts/login/')) {
            if (form.dataset.submitting === 'true') {
                e.preventDefault();
                e.stopPropagation();
                return;
            }
            form.dataset.submitting = 'true';
            const btn = form.querySelector('button[type="submit"]');
            if (btn) {
                btn.style.pointerEvents = 'none';
                btn.style.opacity = '0.8';
                btn.innerHTML = '<span class="inline-flex items-center justify-center gap-2">Entering Watch...</span>';
            }
            // Allow form to submit normally once
            return;
        }
    }, true);

    // -------------------------------------------------------------------------
    // Navigation Responsiveness & Double-Click Protection
    // -------------------------------------------------------------------------
    function showNavProgress() {
        let bar = document.getElementById('wa-nav-progress');
        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'wa-nav-progress';
            bar.style.cssText = 'position:fixed;top:0;left:0;height:2px;background:#b3151b;z-index:99999;width:0%;transition:width 0.35s cubic-bezier(0.1, 0.9, 0.2, 1);box-shadow:0 0 8px rgba(179,21,27,0.8);pointer-events:none;';
            document.body.appendChild(bar);
        }
        bar.getBoundingClientRect();
        bar.style.width = '75%';
    }

    window.addEventListener('pageshow', function () {
        window.__waNavigating = false;
        const bar = document.getElementById('wa-nav-progress');
        if (bar) {
            bar.style.width = '100%';
            setTimeout(function () {
                if (bar && bar.parentNode) bar.parentNode.removeChild(bar);
            }, 180);
        }
    });

    // Stop click bubbling on all inline buttons to prevent card navigation,
    // and provide instant feedback + double-click protection on page navigation.
    document.addEventListener('click', function (e) {
        const actionBtn = e.target.closest('.wa-checkbox-btn, .wa-habit-btn, [data-inline-action], form button');
        if (actionBtn) {
            e.stopPropagation();
            return;
        }

        const link = e.target.closest('a');
        if (!link || !link.href) return;

        // Skip non-primary clicks, modifiers, target=_blank, and downloads
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || link.target === '_blank' || link.hasAttribute('download')) {
            return;
        }

        try {
            const dest = new URL(link.href, window.location.origin);
            if (dest.origin !== window.location.origin) return;
            // Same-page anchors
            if (dest.pathname === window.location.pathname && dest.search === window.location.search && dest.hash) return;
            if (dest.pathname.startsWith('/api/') || dest.pathname.includes('/logout')) return;

            // Prevent duplicate clicks in-flight
            if (window.__waNavigating) {
                e.preventDefault();
                return;
            }

            window.__waNavigating = true;
            link.style.opacity = '0.75';
            showNavProgress();
        } catch (err) {}
    }, false);

})();

