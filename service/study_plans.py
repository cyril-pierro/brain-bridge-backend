from typing import List, Dict, Union
from uuid import UUID
from datetime import date, timedelta
from sqlalchemy.orm import joinedload

from model.study_plans import StudyPlan, DailyStudySession, DayOfWeek
from model.courses import Course
from util.enum import SubjectType
from core.db import CreateAsyncDBSession
from service.redis import AsyncRedis
from sqlalchemy import select

async_redis_instance = AsyncRedis()


class StudyPlanService:
    @staticmethod
    def categorize_subjects(courses: List[Course]) -> Dict[str, List[Course]]:
        """Categorizes courses using the SubjectType enum from the Course model."""
        categorized = {"core": [], "electives": []}
        for course in courses:
            if course.type == SubjectType.CORE:
                categorized["core"].append(course)
            else:
                categorized["electives"].append(course)
        return categorized

    @staticmethod
    def get_weekly_frequency(num_subjects: int) -> Dict[str, Union[str, int]]:
        if num_subjects <= 2:
            return {"strategy": "frequent", "min": 2}
        elif num_subjects <= 4:
            return {"strategy": "balanced", "min": 1}
        return {"strategy": "rotate", "min": 1}

    @staticmethod
    def allocate_subjects_to_days(core: List[Course], electives: List[Course], strengths: Dict[int, int]) -> Dict[DayOfWeek, Course]:
        days = list(DayOfWeek)
        # Sort: Core first, then by strength (weaker subjects have lower strength values)
        all_subjects = sorted(
            core + electives, key=lambda c: (0 if c in core else 1, strengths.get(c.id, 3)))

        if not all_subjects:
            return {}

        freq = StudyPlanService.get_weekly_frequency(len(all_subjects))
        allocation = {}

        pool = []
        for s in all_subjects:
            pool.extend([s] * freq["min"])

        # Fill to 5 days
        idx = 0
        while len(pool) < 5:
            pool.append(all_subjects[idx % len(all_subjects)])
            idx += 1

        for i, day in enumerate(days):
            allocation[day] = pool[i]

        return allocation

    @staticmethod
    def generate_tasks(daily_study_time: int) -> List[Dict]:
        """Micro-task duration scaling."""
        if daily_study_time <= 30:
            return [
                {"type": "reading", "duration": daily_study_time // 2},
                {"type": "quiz", "duration": daily_study_time -
                    (daily_study_time // 2)}
            ]

        reading = 20 if daily_study_time >= 45 else 15
        flashcards = 15 if daily_study_time >= 45 else 10
        quiz = daily_study_time - (reading + flashcards)

        return [
            {"type": "reading", "duration": reading},
            {"type": "flashcards", "duration": flashcards},
            {"type": "quiz", "duration": quiz}
        ]

    @staticmethod
    async def generate_study_plan_async(user_id: UUID, data) -> StudyPlan:
        # 1. OPTIMIZED FETCH:
        # We explicitly join only Topics. We ignore 'flashcards' and 'quiz_questions'
        # to keep the memory footprint small.
        async with CreateAsyncDBSession() as session:
            stmt = select(Course).options(
                joinedload(Course.topics)
            ).filter(Course.id.in_(data.selected_subjects))
            result = await session.execute(stmt)
            courses = result.scalars().all()

        categorized = StudyPlanService.categorize_subjects(courses)
        strengths = {s.course_id: s.strength for s in data.strength_ratings}

        allocation = StudyPlanService.allocate_subjects_to_days(
            categorized["core"], categorized["electives"], strengths
        )

        week_start = date.today() - timedelta(days=date.today().weekday())

        # 2. BULK TRANSACTION
        async with CreateAsyncDBSession() as session:
            study_plan = StudyPlan(user_id=user_id, week_start_date=week_start)
            session.add(study_plan)
            await session.flush()

            daily_sessions = []
            for day, course in allocation.items():
                # Here we use the Topic objects attached to the course
                # Since your Course model has: order_by="Topic.order"
                # the list 'course.topics' is already sorted correctly.

                # We use a generator expression to find the first uncompleted Topic
                topic = next(
                    (t for t in course.topics if t.id not in data.completed_topics),
                    None
                )

                # Fallback: If all topics are completed, repeat the last Topic in the syllabus
                if not topic and course.topics:
                    topic = course.topics[-1]

                if topic:
                    daily_sessions.append(DailyStudySession(
                        study_plan_id=study_plan.id,
                        day_of_week=day,
                        course_id=course.id,
                        topic_id=topic.id,  # Using Topic model ID
                        tasks=StudyPlanService.generate_tasks(
                            data.daily_study_time)
                    ))

            session.add_all(daily_sessions)
            await session.commit()
            return study_plan

    @staticmethod
    async def swap_days_async(user_id: UUID, from_day: DayOfWeek, to_day: DayOfWeek) -> bool:
        """
        Optimized Swap: Fetches only the two relevant sessions and swaps them
        in one transaction to minimize DB overhead.
        """
        # Calculate current week start
        week_start = date.today() - timedelta(days=date.today().weekday())

        async with CreateAsyncDBSession() as session:
            # 1. Find the plan ID first
            stmt = select(StudyPlan.id).filter(
                StudyPlan.user_id == user_id,
                StudyPlan.week_start_date == week_start
            )
            result = await session.execute(stmt)
            plan_id = result.scalar_one_or_none()

            if not plan_id:
                return False

            # 2. Fetch both sessions in ONE query using the 'in_' operator
            stmt = select(DailyStudySession).filter(
                DailyStudySession.study_plan_id == plan_id,
                DailyStudySession.day_of_week.in_([from_day, to_day])
            )
            result = await session.execute(stmt)
            sessions = result.scalars().all()

            # 3. Ensure we have both sessions to perform a swap
            if len(sessions) == 2:
                # Swap the Enum values in memory
                sessions[0].day_of_week, sessions[1].day_of_week = \
                    sessions[1].day_of_week, sessions[0].day_of_week

                await session.commit()
                return True

            return False
