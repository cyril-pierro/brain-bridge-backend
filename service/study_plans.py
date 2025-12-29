from model.study_plans import StudyPlan, DailyStudySession, DayOfWeek
from model.courses import Course
from model.topics import Topic
from schema.study_plans import (
    StudyPlanGenerateIn, StudyPlanOut,
    DailyStudySessionOut,
    TaskOut
)
from datetime import date, timedelta
from typing import List, Dict, Optional, Union
from uuid import UUID
from service.redis import Redis

redis_instance = Redis()


class StudyPlanService:

    @staticmethod
    def categorize_subjects(courses: List[Course]) -> Dict[str, List[Course]]:
        # OPTIMIZED: Cache core course names to avoid repeated database queries
        cache_key = "core_course_names"
        cached_names = redis_instance.get_json(cache_key)

        if cached_names:
            core_course_names = cached_names
        else:
            core_course_names = Course.get_core_course_names()
            redis_instance.set_json(
                cache_key, core_course_names, expiry=3600)  # Cache for 1 hour

        core = []
        electives = []
        for course in courses:
            if course.name in core_course_names:
                core.append(course)
            else:
                electives.append(course)
        return {"core": core, "electives": electives}

    @staticmethod
    def get_weekly_frequency(num_subjects: int) -> Dict[str, Union[str, int]]:
        """Return frequency strategy based on subject count."""
        if num_subjects <= 2:
            return {"strategy": "frequent",
                    "min_appearances": 2, "max_appearances": 3}
        elif num_subjects <= 4:
            return {"strategy": "balanced",
                    "min_appearances": 1, "max_appearances": 2}
        elif num_subjects <= 6:
            return {"strategy": "rotate",
                    "min_appearances": 1, "max_appearances": 1}
        else:  # 7-8 subjects
            return {"strategy": "priority_rotate",
                    "min_appearances": 1, "max_appearances": 1}

    @staticmethod
    def allocate_subjects_to_days(
        core_courses: List[Course],
        elective_courses: List[Course],
        strength_ratings: Dict[int, int]
    ) -> Dict[DayOfWeek, Course]:
        """Allocate subjects to weekdays following the specified algorithm."""
        days = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]
        allocation = {}

        all_subjects = core_courses + elective_courses
        total_subjects = len(all_subjects)

        if total_subjects == 0:
            return allocation

        # Get frequency strategy
        freq_strategy = StudyPlanService.get_weekly_frequency(total_subjects)

        # Sort subjects by priority: weaker core subjects first, then weaker electives
        def sort_key(course):
            strength = strength_ratings.get(course.id, 3)
            is_core = course in core_courses
            # Core subjects get priority (lower sort value), then by weakness (lower strength first)
            return (0 if is_core else 1, strength)

        sorted_subjects = sorted(all_subjects, key=sort_key)

        # For small numbers, assign based on frequency
        if freq_strategy["strategy"] in ["frequent", "balanced"]:
            # Calculate how many times each subject should appear
            subject_counts = {}
            remaining_slots = len(days)

            # First pass: assign minimum appearances
            for subject in sorted_subjects:
                min_count = freq_strategy["min_appearances"]
                subject_counts[subject.id] = min_count
                remaining_slots -= min_count

            # Distribute remaining slots to weaker subjects
            if remaining_slots > 0:
                for subject in sorted_subjects:
                    if remaining_slots <= 0:
                        break
                    max_extra = freq_strategy["max_appearances"] - \
                        subject_counts[subject.id]
                    can_add = min(remaining_slots, max_extra)
                    subject_counts[subject.id] += can_add
                    remaining_slots -= can_add

            # Create the allocation list
            allocation_list = []
            for subject in sorted_subjects:
                count = subject_counts[subject.id]
                allocation_list.extend([subject] * count)

            # If we have more slots than allocated, fill with rotation
            while len(allocation_list) < len(days):
                allocation_list.extend(sorted_subjects)

            # Assign to days
            for i, day in enumerate(days):
                if i < len(allocation_list):
                    allocation[day] = allocation_list[i]

        else:  # rotate or priority_rotate
            # Simple rotation: assign one subject per day, cycling through all
            for i, day in enumerate(days):
                subject_index = i % len(sorted_subjects)
                allocation[day] = sorted_subjects[subject_index]

        # Ensure no consecutive same subject (final check)
        day_list = list(days)
        for i in range(1, len(day_list)):
            current_day = day_list[i]
            prev_day = day_list[i-1]
            if (current_day in allocation and prev_day in allocation and
                    allocation[current_day].id == allocation[prev_day].id):
                # Find a different subject to swap with
                for j in range(i + 1, len(day_list)):
                    swap_day = day_list[j]
                    if (swap_day in allocation and
                            allocation[swap_day].id != allocation[current_day].id):
                        # Swap
                        allocation[current_day], allocation[swap_day] = allocation[swap_day], allocation[current_day]
                        break

        return allocation

    @staticmethod
    def select_topic_for_course(course: Course,
                                completed_topic_ids: List[int]) -> Optional[Topic]:
        available_topics = [t for t in course.topics
                            if t.id not in completed_topic_ids]
        if not available_topics:
            # If all topics completed, repeat the last topic or any topic
            return course.topics[-1] if course.topics else None

        # Sort by syllabus order (ascending order number)
        ordered_topics = sorted(available_topics, key=lambda t: t.order)

        # Prefer examinable/high-weight topics, but for now just return next in order
        # TODO: Add logic for examinable topics when topic model has that field
        return ordered_topics[0]

    @staticmethod
    def generate_tasks(daily_study_time: int) -> List[Dict[str, Union[str, int]]]:
        """Generate micro-tasks for the daily study session."""
        # Base task structure following the requirements
        base_tasks = [
            {"type": "reading", "duration": 10},  # Topic reading
            # Flashcards or past questions
            {"type": "flashcards", "duration": 5},
            {"type": "quiz", "duration": 10},  # Quiz or past question practice
        ]

        # Scale durations based on available time
        if daily_study_time <= 30:
            # Minimal time: focus on essentials
            tasks = [
                {"type": "reading", "duration": max(
                    10, daily_study_time // 2)},
                {"type": "quiz", "duration": max(
                    5, daily_study_time - (daily_study_time // 2))},
            ]
        elif daily_study_time <= 45:
            # Short session: reading + practice
            tasks = [
                {"type": "reading", "duration": 15},
                {"type": "flashcards", "duration": 10},
                {"type": "quiz", "duration": 15},
            ]
        else:
            # Full session: all tasks
            tasks = [
                {"type": "reading", "duration": 20},
                {"type": "flashcards", "duration": 15},
                {"type": "quiz", "duration": 20},
            ]

        # Adjust to fit exact time
        total_duration = sum(task["duration"] for task in tasks)
        if total_duration > daily_study_time:
            # Reduce durations proportionally
            scale_factor = daily_study_time / total_duration
            for task in tasks:
                task["duration"] = max(5, int(task["duration"] * scale_factor))
        elif total_duration < daily_study_time:
            # Distribute extra time to reading and quiz
            extra_time = daily_study_time - total_duration
            tasks[0]["duration"] += extra_time // 2
            tasks[2]["duration"] += extra_time - (extra_time // 2)

        return tasks

    @staticmethod
    def generate_study_plan(user_id: UUID, data: StudyPlanGenerateIn) -> StudyPlan:
        # OPTIMIZED: Bulk load all courses in a single query instead of N+1 queries
        courses = Course.get_courses_by_ids(data.selected_subjects)
        courses = [c for c in courses if c]

        # Categorize
        categorized = StudyPlanService.categorize_subjects(courses)
        core = categorized["core"]
        electives = categorized["electives"]

        # Strength dict
        strength_dict = {
            s.course_id: s.strength for s in data.strength_ratings}

        # Allocate to days
        allocation = StudyPlanService.allocate_subjects_to_days(
            core, electives, strength_dict)

        # Create study plan
        week_start = date.today() - timedelta(days=date.today().weekday())  # Monday
        study_plan = StudyPlan(user_id=user_id, week_start_date=week_start)
        study_plan.save()

        # Create daily sessions
        for day, course in allocation.items():
            topic = StudyPlanService.select_topic_for_course(
                course, data.completed_topics)
            if not topic:
                continue
            tasks = StudyPlanService.generate_tasks(data.daily_study_time)
            session = DailyStudySession(
                study_plan_id=study_plan.id,
                day_of_week=day,
                course_id=course.id,
                topic_id=topic.id,
                tasks=tasks
            )
            session.save()

        return study_plan

    @staticmethod
    def get_current_week_plan(user_id: UUID) -> Optional[StudyPlanOut]:
        week_start = date.today() - timedelta(days=date.today().weekday())
        plan = StudyPlan.get_current_week_plan(user_id, week_start)
        if not plan:
            return None

        # Build Pydantic models with relationships accessed while session is active
        daily_sessions = []
        for session in plan.daily_sessions:
            tasks = [TaskOut(**task) for task in session.tasks]
            daily_session = DailyStudySessionOut(
                id=session.id,
                day_of_week=session.day_of_week,
                course_id=session.course_id,
                course_name=session.course.name,
                topic_id=session.topic_id,
                topic_subject=session.topic.subject,
                tasks=tasks
            )
            daily_sessions.append(daily_session)

        return StudyPlanOut(
            id=plan.id,
            user_id=str(plan.user_id),
            week_start_date=plan.week_start_date,
            daily_sessions=daily_sessions
        )

    @staticmethod
    def swap_days(user_id: UUID, from_day: DayOfWeek, to_day: DayOfWeek):
        week_start = date.today() - timedelta(days=date.today().weekday())
        plan = StudyPlan.get_current_week_plan(user_id, week_start)
        if not plan:
            return False

        sessions = DailyStudySession.get_sessions_for_plan(plan.id)
        from_session = next(
            (s for s in sessions if s.day_of_week == from_day), None)
        to_session = next(
            (s for s in sessions if s.day_of_week == to_day), None)

        if from_session and to_session:
            from_session.day_of_week, to_session.day_of_week = to_session.day_of_week, from_session.day_of_week
            from_session.save()
            to_session.save()
            return True
        return False
