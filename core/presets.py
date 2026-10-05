"""
Winter Arc Preset Library & Blueprint Architecture.

Provides structured, user-customizable blueprints for launching a Winter Arc.
These templates represent starting blueprints, NOT official or immutable rules.
Users can review, customize, add, remove, and rename goals, milestones, tasks,
and habits prior to committing to The Oath and activating their Arc.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class MilestoneBlueprint:
    title: str
    target_value: Optional[float] = None
    days_offset: Optional[int] = 30

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'target_value': self.target_value,
            'days_offset': self.days_offset,
        }


@dataclass
class TaskBlueprint:
    title: str
    description: str = ''
    priority: int = 2  # 1=High, 2=Medium, 3=Low
    days_offset: Optional[int] = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'days_offset': self.days_offset,
        }


@dataclass
class GoalBlueprint:
    title: str
    description: str = ''
    category: str = 'OTHER'  # HEALTH, PRODUCTIVITY, LEARNING, FINANCE, OTHER
    priority: int = 1
    milestones: List[MilestoneBlueprint] = field(default_factory=list)
    tasks: List[TaskBlueprint] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'priority': self.priority,
            'milestones': [m.to_dict() for m in self.milestones],
            'tasks': [t.to_dict() for t in self.tasks],
        }


@dataclass
class HabitBlueprint:
    name: str
    description: str = ''
    frequency: str = 'DAILY'  # DAILY, WEEKLY, SELECTED_DAYS, TARGET_COUNT
    target_count: int = 1
    target_label: str = '1 session'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'frequency': self.frequency,
            'target_count': self.target_count,
            'target_label': self.target_label,
        }


@dataclass
class PresetDefinition:
    key: str
    name: str
    tagline: str
    description: str
    objective: str
    recommended_duration_days: int = 90
    goals: List[GoalBlueprint] = field(default_factory=list)
    habits: List[HabitBlueprint] = field(default_factory=list)

    @property
    def goal_count(self) -> int:
        return len(self.goals)

    @property
    def habit_count(self) -> int:
        return len(self.habits)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'name': self.name,
            'tagline': self.tagline,
            'description': self.description,
            'objective': self.objective,
            'recommended_duration_days': self.recommended_duration_days,
            'goal_count': self.goal_count,
            'habit_count': self.habit_count,
            'goals': [g.to_dict() for g in self.goals],
            'habits': [h.to_dict() for h in self.habits],
        }


# ==============================================================================
# BLUEPRINT DEFINITIONS
# ==============================================================================

PRESET_CLASSIC = PresetDefinition(
    key='classic',
    name='Classic Winter Arc',
    tagline='Balanced discipline',
    description='A balanced 90-day discipline blueprint for building consistency across body, mind, focus, and recovery.',
    objective='Build physical discipline, mental clarity, focused work, and consistent daily habits.',
    recommended_duration_days=90,
    habits=[
        HabitBlueprint(
            name='Daily Movement',
            description='30 minutes of intentional physical activity, mobility, or workout.',
            frequency='DAILY',
            target_count=30,
            target_label='30 minutes',
        ),
        HabitBlueprint(
            name='Read / Study',
            description='30 minutes of dedicated reading, research, or active study.',
            frequency='DAILY',
            target_count=30,
            target_label='30 minutes',
        ),
        HabitBlueprint(
            name='Sleep Discipline',
            description='Adhere to a consistent sleep and wake schedule for deep physical and mental recovery.',
            frequency='DAILY',
            target_count=1,
            target_label='Sleep target',
        ),
        HabitBlueprint(
            name='Limit Mindless Scrolling',
            description='Strict daily boundaries on doomscrolling, short-form feeds, and passive distraction.',
            frequency='DAILY',
            target_count=1,
            target_label='Boundary kept',
        ),
        HabitBlueprint(
            name='Daily Reflection',
            description='Evening review of the day’s actions, lessons learned, and tomorrow’s non-negotiables.',
            frequency='DAILY',
            target_count=1,
            target_label='1 reflection',
        ),
    ],
    goals=[
        GoalBlueprint(
            title='Build Physical Discipline',
            description='Develop baseline physical strength, endurance, and unyielding movement consistency.',
            category='HEALTH',
            priority=1,
            milestones=[
                MilestoneBlueprint(title='Establish 30-day consistent movement baseline', days_offset=30),
                MilestoneBlueprint(title='Mid-Arc conditioning and stamina benchmark review', days_offset=60),
                MilestoneBlueprint(title='Complete full 90 days of physical training discipline', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Design weekly movement and training schedule', description='Plan split, rest days, and workout timing.', priority=1, days_offset=2),
                TaskBlueprint(title='Prepare training apparel and dedicated workout space', priority=2, days_offset=3),
            ],
        ),
        GoalBlueprint(
            title='Strengthen Mental Discipline',
            description='Cultivate deep focus, active learning, and intellectual stamina throughout the winter.',
            category='LEARNING',
            priority=1,
            milestones=[
                MilestoneBlueprint(title='Complete first core reading selection and capture notes', days_offset=30),
                MilestoneBlueprint(title='Finish second study curriculum or core book', days_offset=60),
                MilestoneBlueprint(title='Synthesize quarterly insights and personal principles', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Select 3 foundational books or curriculum topics for the season', priority=1, days_offset=2),
                TaskBlueprint(title='Set up a distraction-free study space', priority=2, days_offset=3),
            ],
        ),
        GoalBlueprint(
            title='Protect Focus & Recovery',
            description='Guard mental energy, streamline sleep routines, and reclaim attention from shallow feeds.',
            category='PRODUCTIVITY',
            priority=2,
            milestones=[
                MilestoneBlueprint(title='14 consecutive days of rigid screen-off sleep cutoff', days_offset=20),
                MilestoneBlueprint(title='Mid-season digital consumption audit', days_offset=50),
                MilestoneBlueprint(title='Lock in permanent recovery and attention protocols', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Configure app screen-time limits and night-time downtime', priority=1, days_offset=1),
                TaskBlueprint(title='Establish an evening screen-free wind-down ritual', priority=2, days_offset=2),
            ],
        ),
    ],
)


PRESET_STUDENT = PresetDefinition(
    key='student',
    name='Student Lock-In',
    tagline='Study + skill + health',
    description='A Winter Arc blueprint designed around academic consistency, skill development, health, and disciplined routines.',
    objective='Achieve academic excellence, build core technical skills, and maintain physical discipline through structured daily routines.',
    recommended_duration_days=90,
    habits=[
        HabitBlueprint(
            name='Deep Study',
            description='60 minutes of uninterrupted syllabus, course material, or academic study.',
            frequency='DAILY',
            target_count=60,
            target_label='60 minutes',
        ),
        HabitBlueprint(
            name='Coding / Skill Practice',
            description='60 minutes of hands-on coding, algorithm practice, or practical skill building.',
            frequency='DAILY',
            target_count=60,
            target_label='60 minutes',
        ),
        HabitBlueprint(
            name='Revision',
            description='30 minutes of spaced repetition, flashcards, or active recall review.',
            frequency='DAILY',
            target_count=30,
            target_label='30 minutes',
        ),
        HabitBlueprint(
            name='Physical Movement',
            description='30 minutes of daily exercise to sustain energy and cognitive stamina.',
            frequency='DAILY',
            target_count=30,
            target_label='30 minutes',
        ),
        HabitBlueprint(
            name='Sleep Discipline',
            description='Consistent sleep timing to consolidate long-term memory and maintain alertness.',
            frequency='DAILY',
            target_count=1,
            target_label='Sleep target',
        ),
    ],
    goals=[
        GoalBlueprint(
            title='Academic Progress',
            description='Master syllabus concepts and complete all scheduled exam preparation checkpoints.',
            category='LEARNING',
            priority=1,
            milestones=[
                MilestoneBlueprint(title='Complete first-half syllabus revision and lecture notes', days_offset=45),
                MilestoneBlueprint(title='Finish comprehensive mock exams and subject reviews', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Map syllabus topics, assignment deadlines, and exam dates', priority=1, days_offset=2),
                TaskBlueprint(title='Organize subject notes into clear revision folders', priority=2, days_offset=4),
            ],
        ),
        GoalBlueprint(
            title='Technical Skill Development',
            description='Build real-world programming proficiency and problem-solving capability.',
            category='LEARNING',
            priority=1,
            milestones=[
                MilestoneBlueprint(title='Build consistent coding practice with 30-day streak', days_offset=30),
                MilestoneBlueprint(title='Complete core technical project architecture and implementation', days_offset=60),
                MilestoneBlueprint(title='Solve defined technical challenge problem set', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Configure development tools, Git repo, and environment', priority=1, days_offset=2),
                TaskBlueprint(title='Select weekly algorithm problem sets or tutorial modules', priority=2, days_offset=5),
            ],
        ),
        GoalBlueprint(
            title='Physical & Mental Discipline',
            description='Prevent academic burnout through daily physical movement and mental balance.',
            category='HEALTH',
            priority=2,
            milestones=[
                MilestoneBlueprint(title='Sustain 45 days of zero-burnout study and movement routine', days_offset=45),
                MilestoneBlueprint(title='Maintain physical movement routine straight through exam periods', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Design study break and movement protocol (Pomodoro cadence)', priority=2, days_offset=2),
            ],
        ),
    ],
)


PRESET_FITNESS = PresetDefinition(
    key='fitness',
    name='Fitness Arc',
    tagline='Training + recovery',
    description='A physical-discipline blueprint focused on movement, training, nutrition, recovery, and consistency.',
    objective='Build unshakeable physical stamina, consistent training habits, structured nutrition, and disciplined recovery.',
    recommended_duration_days=90,
    habits=[
        HabitBlueprint(
            name='Training / Workout',
            description='45 minutes of structured resistance training, conditioning, or athletic movement.',
            frequency='DAILY',
            target_count=45,
            target_label='45 minutes',
        ),
        HabitBlueprint(
            name='Daily Steps / Movement',
            description='Daily step baseline or active non-exercise physical activity.',
            frequency='DAILY',
            target_count=10000,
            target_label='10,000 steps',
        ),
        HabitBlueprint(
            name='Nutrition Discipline',
            description='Adhere to whole-food nutritional targets and eliminate mindless snacking.',
            frequency='DAILY',
            target_count=1,
            target_label='Target met',
        ),
        HabitBlueprint(
            name='Hydration',
            description='Maintain adequate hydration throughout the day with consistent water intake.',
            frequency='DAILY',
            target_count=3,
            target_label='3 liters',
        ),
        HabitBlueprint(
            name='Sleep / Recovery',
            description='Prioritize 7–8 hours of restful sleep and proactive muscle recovery.',
            frequency='DAILY',
            target_count=1,
            target_label='Recovery target',
        ),
    ],
    goals=[
        GoalBlueprint(
            title='Build Training Consistency',
            description='Execute progressive training sessions without missing planned workouts.',
            category='HEALTH',
            priority=1,
            milestones=[
                MilestoneBlueprint(title='Log 25 structured workout sessions in first 30 days', days_offset=30),
                MilestoneBlueprint(title='Progressive overload benchmark review at day 60', days_offset=60),
                MilestoneBlueprint(title='Complete full 90-day training cycle with zero skipped weeks', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Finalize 12-week workout split and exercise library', priority=1, days_offset=2),
                TaskBlueprint(title='Establish regular weekly schedule and prepare workout gear', priority=2, days_offset=3),
            ],
        ),
        GoalBlueprint(
            title='Improve Recovery',
            description='Systematize sleep hygiene, mobility, and physical restoration protocols.',
            category='HEALTH',
            priority=2,
            milestones=[
                MilestoneBlueprint(title='30 consecutive days of post-workout mobility routine', days_offset=30),
                MilestoneBlueprint(title='Optimize bedroom temperature, lighting, and sleep schedule', days_offset=60),
            ],
            tasks=[
                TaskBlueprint(title='Set up 10-minute nightly mobility and stretch routine', priority=2, days_offset=2),
            ],
        ),
        GoalBlueprint(
            title='Improve Nutrition Discipline',
            description='Fuel physical performance with disciplined whole foods and balanced hydration.',
            category='HEALTH',
            priority=2,
            milestones=[
                MilestoneBlueprint(title='Zero ultra-processed food lapses for first 30 days', days_offset=30),
                MilestoneBlueprint(title='Maintain structured weekly meal preparation through day 60', days_offset=60),
            ],
            tasks=[
                TaskBlueprint(title='Clear kitchen pantry of processed snacks and sugar', priority=1, days_offset=1),
                TaskBlueprint(title='Establish weekly grocery and meal prep cadence', priority=2, days_offset=4),
            ],
        ),
    ],
)


PRESET_MONK_MODE = PresetDefinition(
    key='monk_mode',
    name='Monk Mode',
    tagline='Focus + attention',
    description='A distraction-control blueprint built around deep work, deliberate attention, reading, and disciplined routines.',
    objective='Eliminate shallow distractions, cultivate deep focus, build mental stillness, and execute on high-leverage priorities.',
    recommended_duration_days=90,
    habits=[
        HabitBlueprint(
            name='Deep Work',
            description='60+ minutes of focused, single-task deep work without notifications or context switching.',
            frequency='DAILY',
            target_count=60,
            target_label='60 minutes',
        ),
        HabitBlueprint(
            name='No Unnecessary Social Media',
            description='Zero passive scrolling, algorithmic feeds, or mindless digital browsing.',
            frequency='DAILY',
            target_count=1,
            target_label='Zero feeds',
        ),
        HabitBlueprint(
            name='Morning Routine',
            description='Complete deliberate morning routine before touching phones or digital screens.',
            frequency='DAILY',
            target_count=1,
            target_label='Morning routine',
        ),
        HabitBlueprint(
            name='Reading',
            description='20 minutes of deliberate reading from physical books or long-form literature.',
            frequency='DAILY',
            target_count=20,
            target_label='20 minutes',
        ),
        HabitBlueprint(
            name='Sleep Discipline',
            description='Strict sleep schedule with digital devices powered off 60 minutes before bed.',
            frequency='DAILY',
            target_count=1,
            target_label='Digital cutoff',
        ),
    ],
    goals=[
        GoalBlueprint(
            title='Protect Attention',
            description='Reclaim cognitive clarity by stripping away digital noise and involuntary dopamine loops.',
            category='PRODUCTIVITY',
            priority=1,
            milestones=[
                MilestoneBlueprint(title='Complete 14 consecutive days of zero social media consumption', days_offset=14),
                MilestoneBlueprint(title='Achieve 45 days of distraction-free work sessions', days_offset=45),
                MilestoneBlueprint(title='Establish permanent digital minimalism lifestyle and boundaries', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Uninstall entertainment apps and activate web blockers', priority=1, days_offset=1),
                TaskBlueprint(title='Set smartphone display to grayscale and mute notifications', priority=1, days_offset=1),
            ],
        ),
        GoalBlueprint(
            title='Build Deep Work Capacity',
            description='Expand mental endurance to sustain prolonged periods of high-intensity cognitive output.',
            category='PRODUCTIVITY',
            priority=1,
            milestones=[
                MilestoneBlueprint(title='Consistently log 2+ hours daily deep work for 30 days', days_offset=30),
                MilestoneBlueprint(title='Ship major high-leverage quarterly deliverable under monk mode', days_offset=60),
            ],
            tasks=[
                TaskBlueprint(title='Block uninterrupted 90-minute morning deep work window on calendar', priority=1, days_offset=2),
            ],
        ),
        GoalBlueprint(
            title='Strengthen Daily Discipline',
            description='Execute morning and evening routines with precision and emotional sovereignty.',
            category='PRODUCTIVITY',
            priority=2,
            milestones=[
                MilestoneBlueprint(title='Unbroken morning routine for 30 consecutive days', days_offset=30),
                MilestoneBlueprint(title='Mid-season solitude and discipline reflection written', days_offset=60),
            ],
            tasks=[
                TaskBlueprint(title='Document 5-step non-negotiable morning protocol', priority=2, days_offset=1),
            ],
        ),
    ],
)


PRESET_MIND_BODY = PresetDefinition(
    key='mind_body',
    name='Mind + Body',
    tagline='Balanced self-discipline',
    description='A balanced blueprint combining physical movement, mental clarity, reflection, reading, and recovery.',
    objective='Harmonize physical vitality with mental stillness through daily movement, thoughtful reflection, and restorative discipline.',
    recommended_duration_days=90,
    habits=[
        HabitBlueprint(
            name='Movement',
            description='30 minutes of intentional, mindful physical activity or endurance training.',
            frequency='DAILY',
            target_count=30,
            target_label='30 minutes',
        ),
        HabitBlueprint(
            name='Reading',
            description='20 minutes of enriching reading in philosophy, psychology, or literature.',
            frequency='DAILY',
            target_count=20,
            target_label='20 minutes',
        ),
        HabitBlueprint(
            name='Reflection / Journal',
            description='Daily written reflection capturing mental state, gratitude, and evening recap.',
            frequency='DAILY',
            target_count=1,
            target_label='1 reflection',
        ),
        HabitBlueprint(
            name='Mindfulness / Quiet Time',
            description='10 minutes of silent meditation, breathwork, or quiet contemplation.',
            frequency='DAILY',
            target_count=10,
            target_label='10 minutes',
        ),
        HabitBlueprint(
            name='Sleep Discipline',
            description='Nurturing 8-hour sleep schedule for neurological restoration.',
            frequency='DAILY',
            target_count=1,
            target_label='Restful sleep',
        ),
    ],
    goals=[
        GoalBlueprint(
            title='Strengthen the Body',
            description='Develop sustainable physical energy, functional mobility, and cardiovascular health.',
            category='HEALTH',
            priority=1,
            milestones=[
                MilestoneBlueprint(title='Establish consistent daily movement habit for 30 days', days_offset=30),
                MilestoneBlueprint(title='Measurable physical endurance and mobility improvement at day 60', days_offset=60),
            ],
            tasks=[
                TaskBlueprint(title='Plan weekly rotation of cardio, resistance, and mobility sessions', priority=1, days_offset=2),
            ],
        ),
        GoalBlueprint(
            title='Strengthen the Mind',
            description='Foster mental clarity, resilience, and philosophical depth through daily reading and introspection.',
            category='LEARNING',
            priority=1,
            milestones=[
                MilestoneBlueprint(title='Complete 60 journal reflections across the season', days_offset=60),
                MilestoneBlueprint(title='Read 3 transformative books during the Arc', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Select first book on philosophy, mindfulness, or stoic discipline', priority=2, days_offset=2),
            ],
        ),
        GoalBlueprint(
            title='Build Consistency',
            description='Integrate mindfulness and quiet contemplation into daily non-negotiable living.',
            category='PRODUCTIVITY',
            priority=2,
            milestones=[
                MilestoneBlueprint(title='30-day streak of daily mindfulness and breathwork', days_offset=30),
                MilestoneBlueprint(title='Full 90-day holistic mind-body integration', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Designate a calm, quiet physical space for meditation', priority=2, days_offset=1),
            ],
        ),
    ],
)


PRESET_CAREER = PresetDefinition(
    key='career',
    name='Career Lock-In',
    tagline='Skills + projects + execution',
    description='A Winter Arc blueprint for focused career development, technical skill building, projects, and disciplined execution.',
    objective='Accelerate career momentum through deep technical mastery, portfolio project shipping, professional outreach, and physical readiness.',
    recommended_duration_days=90,
    habits=[
        HabitBlueprint(
            name='Technical Skill Practice',
            description='60 minutes of advanced skill drills, coding, or architecture practice.',
            frequency='DAILY',
            target_count=60,
            target_label='60 minutes',
        ),
        HabitBlueprint(
            name='Project Work',
            description='60 minutes shipping tangible portfolio features or project components.',
            frequency='DAILY',
            target_count=60,
            target_label='60 minutes',
        ),
        HabitBlueprint(
            name='Learning / Reading',
            description='30 minutes reading industry papers, docs, or domain literature.',
            frequency='DAILY',
            target_count=30,
            target_label='30 minutes',
        ),
        HabitBlueprint(
            name='Career Progress',
            description='Daily proactive action toward career advancement (outreach, writing, networking, applications).',
            frequency='DAILY',
            target_count=1,
            target_label='Daily action',
        ),
        HabitBlueprint(
            name='Physical Movement',
            description='30 minutes workout to sustain physical confidence and stamina.',
            frequency='DAILY',
            target_count=30,
            target_label='30 minutes',
        ),
    ],
    goals=[
        GoalBlueprint(
            title='Build Technical Skills',
            description='Master critical technical competencies that command high industry value.',
            category='LEARNING',
            priority=1,
            milestones=[
                MilestoneBlueprint(title='Complete targeted technical certification or skill curriculum', days_offset=45),
                MilestoneBlueprint(title='Master 2 high-demand modern frameworks or methodologies', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Audit skill gaps against top industry role requirements', priority=1, days_offset=2),
            ],
        ),
        GoalBlueprint(
            title='Build Portfolio Projects',
            description='Architect and ship production-quality projects that demonstrate end-to-end craft.',
            category='PRODUCTIVITY',
            priority=1,
            milestones=[
                MilestoneBlueprint(title='Ship MVP of flagship portfolio project', days_offset=45),
                MilestoneBlueprint(title='Deploy production-ready project with documentation & live demo', days_offset=75),
            ],
            tasks=[
                TaskBlueprint(title='Scope project requirements and write architectural spec', priority=1, days_offset=3),
                TaskBlueprint(title='Initialize GitHub repository and setup CI/CD pipeline', priority=2, days_offset=5),
            ],
        ),
        GoalBlueprint(
            title='Prepare for Career Opportunities',
            description='Polish personal brand, expand professional network, and interview aggressively.',
            category='OTHER',
            priority=2,
            milestones=[
                MilestoneBlueprint(title='Polished resume, portfolio site, and profile live', days_offset=30),
                MilestoneBlueprint(title='Complete 15 targeted professional outreach conversations', days_offset=60),
            ],
            tasks=[
                TaskBlueprint(title='Overhaul resume metrics with concrete quantified impact', priority=1, days_offset=4),
                TaskBlueprint(title='Draft outreach message template and compile target contact list', priority=2, days_offset=7),
            ],
        ),
        GoalBlueprint(
            title='Maintain Physical Discipline',
            description='Keep physical conditioning and energy high during intense career focus.',
            category='HEALTH',
            priority=2,
            milestones=[
                MilestoneBlueprint(title='Zero-burnout energy maintained throughout 90-day push', days_offset=90),
            ],
            tasks=[
                TaskBlueprint(title='Schedule daily non-negotiable movement block', priority=2, days_offset=2),
            ],
        ),
    ],
)


PRESET_CUSTOM = PresetDefinition(
    key='custom',
    name='Custom Arc',
    tagline='Build your own system',
    description='Start from a blank Arc and define your own rules, goals, milestones, tasks, and habits.',
    objective='Define your own seasonal non-negotiable objective.',
    recommended_duration_days=90,
    habits=[],
    goals=[],
)


# Ordered registry of all available presets
PRESETS_REGISTRY: Dict[str, PresetDefinition] = {
    'classic': PRESET_CLASSIC,
    'student': PRESET_STUDENT,
    'fitness': PRESET_FITNESS,
    'monk_mode': PRESET_MONK_MODE,
    'mind_body': PRESET_MIND_BODY,
    'career': PRESET_CAREER,
    'custom': PRESET_CUSTOM,
}


def get_all_presets() -> List[PresetDefinition]:
    """Return all available preset definitions in canonical order."""
    return list(PRESETS_REGISTRY.values())


def get_preset_by_key(key: str) -> Optional[PresetDefinition]:
    """Retrieve a preset definition by its slug key."""
    return PRESETS_REGISTRY.get(key)
