# Winter Arc — Analytics, Progress & Gamification Specification (ANALYTICS_SPEC)

## 1. Overview
Winter Arc never fabricates progress. Every statistic, XP value, streak count, rank level, completion percentage, and horizon chart is derived strictly from actual persisted user records.

---

## 2. Activity & Event Foundation
Meaningful actions create immutable audit and activity logs via the `ActivityEvent` model (`analytics/models.py`).

### Event Types:
* `TASK_CREATED`: User defines a new task.
* `TASK_COMPLETED`: Task successfully marked completed.
* `GOAL_CREATED`: High-level strategic goal added to an Arc.
* `GOAL_COMPLETED`: Parent goal completed (all milestones fulfilled).
* `MILESTONE_COMPLETED`: Checkpoint reached within a goal.
* `HABIT_CREATED`: New recurring habit established.
* `HABIT_COMPLETED`: Habit beacon lit for a local calendar date.
* `JOURNAL_CREATED`: Daily check-in or reflection logged.
* `ARC_STARTED`: New transformation period sworn.
* `ARC_COMPLETED`: Season concluded and finalized.

---

## 3. XP Rules & Centralized Engine
Defined authoritatively in [`gamification/services.py`](file:///c:/Users/seral/OneDrive/Desktop/winter_arc/gamification/services.py):

| Source Type | Action | XP Award | Notes |
|:---|:---|:---:|:---|
| `task` | Task Completed | **50 XP** | Awarded on completion |
| `habit` | Habit Completed (daily) | **30 XP** | Keyed by `(habit_id, local_date)` |
| `milestone` | Checkpoint Completed | **100 XP** | Awarded when milestone toggled done |
| `goal` | Goal Completed | **250 XP** | Awarded when all checkpoints fulfilled |
| `journal` | Daily Reflection / Check-in | **40 XP** | Keyed by `(user_id, local_date)` |
| `arc` | Arc Completed | **500 XP** | Awarded upon marking season completed |

### XP Idempotency Architecture
* **Ledger Model**: `XPEvent` (`gamification/models.py`) with a database-level `unique_together = ('user', 'source_type', 'source_id')`.
* **Behavior**: Calling `award_xp()` uses `get_or_create`. Repeated clicks, page refreshes, and uncomplete/recomplete toggles do **not** award duplicate XP.
* **Total Calculation**: `Total XP = SUM(XPEvent.amount) WHERE user = request.user`.

---

## 4. Rank Ladder & Thresholds
The rank ladder directly follows the Master Winter Arc progression:
**Recruit $\to$ Sentinel $\to$ Ranger $\to$ Warden**

| Tier | Rank Name | Min XP | Max XP | Progression to Next |
|:---:|:---|:---:|:---:|:---|
| **Tier I** | **Recruit** | 0 | 299 | Target: 300 XP (Sentinel) |
| **Tier II** | **Sentinel** | 300 | 899 | Target: 900 XP (Ranger) |
| **Tier III** | **Ranger** | 900 | 1,999 | Target: 2,000 XP (Warden) |
| **Tier IV** | **Warden** | 2,000 | $\infty$ | Maximum rank attained |

---

## 5. Progress Formulas
Centralized in [`analytics/progress_services.py`](file:///c:/Users/seral/OneDrive/Desktop/winter_arc/analytics/progress_services.py):

* **Arc Progress (%)**:
  $$\text{Arc Progress} = \frac{\sum_{g \in \text{Goals}} \text{Goal Progress}(g)}{|\text{Goals}|}$$
  *(If Arc is marked `COMPLETED`, returns 100%. If Arc has no goals, returns 0% unless completed).*
* **Goal Progress (%)**:
  $$\text{Goal Progress} = \frac{\text{Completed Milestones}}{\text{Total Milestones}} \times 100$$
* **Task Completion Rate (%)**:
  $$\text{Task Rate} = \frac{\text{Completed Tasks}}{\text{Total Tasks (excluding cancelled)}} \times 100$$
* **Habit Consistency (30-day %)**:
  $$\text{Consistency} = \frac{\text{Total Habit Completions in last 30 days}}{\text{Active Habits} \times 30} \times 100$$
* **Habit Current Streak**:
  Consecutive days completed backwards starting from user's local today (or yesterday if today is not yet done).
* **Habit Best Streak**:
  Longest unbroken consecutive day chain across entire completion history.

---

## 6. Deterministic Achievements
Seeded with deterministic unlock rules and one-time XP bonuses:
* `FIRST_TASK` ("The First Step"): Completed first task (+50 XP).
* `FIRST_GOAL` ("Oathkeeper"): Fulfilled first strategic goal (+100 XP).
* `STREAK_7` ("The 7-Day Flame"): Reached a 7-day habit streak (+150 XP).
* `STREAK_30` ("Iron Will"): Reached a 30-day habit streak (+300 XP).
* `FIRST_ARC` ("Season Complete"): Successfully concluded a full Arc (+500 XP).

---

## 7. Security & User Isolation
* Strictly enforced via authenticated context (`user = request.user`).
* All database queries, aggregates, and activity feeds filter by `user=request.user`.
* Verified by Playwright E2E browser tests: User B sees clean empty states (0 XP, Recruit rank, empty ledger) with zero data bleeding from User A.
