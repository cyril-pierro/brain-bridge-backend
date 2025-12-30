from fastapi import HTTPException
from uuid import UUID

from schema.study_plans import (
    StudyPlanOut, DailyStudySessionOut,
    TaskOut, SubjectStrengthOut
)
from schema import SuccessOut
from service.study_plans import StudyPlanService
from model.study_plans import StudyPlan, DailyStudySession, SubjectStrength
from util.serialize import serialize_data
from core.db import CreateAsyncDBSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select
from service.redis import AsyncRedis
from datetime import datetime

async_redis_instance = AsyncRedis()


class StudyPlanController:
    @staticmethod
    def _map_plan(plan: StudyPlan) -> StudyPlanOut:
        """Centralized mapper to reduce code duplication and processing overhead."""
        if not plan:
            return None

        return StudyPlanOut(
            id=plan.id,
            user_id=str(plan.user_id),
            week_start_date=plan.week_start_date,
            daily_sessions=[
                DailyStudySessionOut(
                    id=s.id,
                    day_of_week=s.day_of_week,
                    course_id=s.course_id,
                    course_name=s.course.name,
                    topic_id=s.topic_id,
                    topic_subject=s.topic.subject,
                    tasks=[TaskOut(**t) for t in s.tasks]
                ) for s in plan.daily_sessions
            ]
        )

    @staticmethod
    async def generate_study_plan_async(user_id: str, data):
        try:
            await StudyPlanService.generate_study_plan_async(UUID(user_id), data)
            await async_redis_instance.delete(f"user_current_week_plan:{user_id}")
            await async_redis_instance.delete(f"user_study_plans:{user_id}")
            return SuccessOut(message="Study plan generated successfully")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    async def get_study_plan_by_week_async(user_id: str, week_date: str):
        try:
            target_date = datetime.fromisoformat(week_date).date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        async with CreateAsyncDBSession() as session:
            stmt = select(StudyPlan).options(
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.course),
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.topic)
            ).filter(
                StudyPlan.user_id == UUID(user_id),
                StudyPlan.week_start_date == target_date
            )

            result = await session.execute(stmt)
            plan = result.scalar_one_or_none()

        if not plan:
            raise HTTPException(
                status_code=404, detail="No plan found for this week")
        return StudyPlanController._map_plan(plan)

    # Async versions for better performance
    @staticmethod
    async def get_current_week_plan_async(user_id: str):
        """Async version of get_current_week_plan"""
        cache_key = f"user_current_week_plan:{user_id}"
        cached = await async_redis_instance.get_json(cache_key)
        if cached:
            return StudyPlanOut(**cached)

        async with CreateAsyncDBSession() as session:
            stmt = select(StudyPlan).options(
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.course),
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.topic)
            ).filter(StudyPlan.user_id == UUID(user_id)).order_by(StudyPlan.id.desc()).limit(1)

            result = await session.execute(stmt)
            plan = result.scalar_one_or_none()

        mapped_result = StudyPlanController._map_plan(plan)
        if mapped_result:
            await async_redis_instance.set_json(cache_key, serialize_data(mapped_result.model_dump()), expiry=1800)
        return mapped_result

    @staticmethod
    async def get_user_study_plans_async(user_id: str):
        """Async version of get_user_study_plans"""
        cache_key = f"user_study_plans:{user_id}"
        cached = await async_redis_instance.get_json(cache_key)
        if cached:
            return [StudyPlanOut(**p) for p in cached]

        async with CreateAsyncDBSession() as session:
            stmt = select(StudyPlan).options(
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.course),
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.topic)
            ).filter(StudyPlan.user_id == UUID(user_id))

            result = await session.execute(stmt)
            plans = result.scalars().all()

        mapped_results = [StudyPlanController._map_plan(p) for p in plans]
        await async_redis_instance.set_json(
            cache_key,
            [serialize_data(r.model_dump()) for r in mapped_results],
            expiry=1800
        )
        return mapped_results

    @staticmethod
    async def update_strength_async(user_id: str, course_id: int, strength: int):
        async with CreateAsyncDBSession() as session:
            stmt = select(SubjectStrength).filter_by(
                user_id=UUID(user_id), course_id=course_id
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.strength = strength
            else:
                session.add(SubjectStrength(
                    user_id=UUID(user_id), course_id=course_id, strength=strength
                ))
            await session.commit()
        return SuccessOut(message="Strength updated")

    @staticmethod
    async def get_user_strengths_async(user_id: str):
        """Optimized strength fetching with joined course names."""
        async with CreateAsyncDBSession() as session:
            stmt = select(SubjectStrength).options(
                joinedload(SubjectStrength.course)
            ).filter(SubjectStrength.user_id == UUID(user_id))
            result = await session.execute(stmt)
            strengths = result.scalars().all()

            return [
                SubjectStrengthOut(
                    id=s.id,
                    course_id=s.course_id,
                    course_name=s.course.name,
                    strength=s.strength
                ) for s in strengths
            ]

    @staticmethod
    async def swap_days_async(user_id: str, data):
        if await StudyPlanService.swap_days_async(UUID(user_id), data.from_day, data.to_day):
            await async_redis_instance.delete(f"user_current_week_plan:{user_id}")
            return SuccessOut(message="Days swapped successfully")
        raise HTTPException(status_code=400, detail="Swap failed")

    @staticmethod
    async def delete_study_plan_async(user_id: str, plan_id: int):
        async with CreateAsyncDBSession() as session:
            stmt = select(StudyPlan).filter_by(
                id=plan_id, user_id=UUID(user_id))
            result = await session.execute(stmt)
            plan = result.scalar_one_or_none()
            if not plan:
                raise HTTPException(status_code=404, detail="Plan not found")
            await session.delete(plan)
            await session.commit()

        await async_redis_instance.delete(f"user_current_week_plan:{user_id}")
        await async_redis_instance.delete(f"user_study_plans:{user_id}")
        return SuccessOut(message="Study plan deleted successfully")

    @staticmethod
    async def get_study_plan_by_id_async(user_id: str, plan_id: int):
        """Fetches a specific plan by ID, verifying ownership."""
        async with CreateAsyncDBSession() as session:
            stmt = select(StudyPlan).options(
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.course),
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.topic)
            ).filter(
                StudyPlan.id == plan_id,
                StudyPlan.user_id == UUID(user_id)
            )

            result = await session.execute(stmt)
            plan = result.scalar_one_or_none()

        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found")

        return StudyPlanController._map_plan(plan)
