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
from core.db import CreateDBSession
from sqlalchemy.orm import joinedload
from service.redis import Redis
from datetime import datetime

redis_instance = Redis()


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
    def generate_study_plan(user_id: str, data):
        try:
            StudyPlanService.generate_study_plan(UUID(user_id), data)
            redis_instance.delete(f"user_current_week_plan:{user_id}")
            redis_instance.delete(f"user_study_plans:{user_id}")
            return SuccessOut(message="Study plan generated successfully")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    def get_current_week_plan(user_id: str):
        cache_key = f"user_current_week_plan:{user_id}"
        if cached := redis_instance.get_json(cache_key):
            return StudyPlanOut(**cached)

        with CreateDBSession() as session:
            plan = session.query(StudyPlan).options(
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.course),
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.topic)
            ).filter(StudyPlan.user_id == UUID(user_id)).order_by(StudyPlan.id.desc()).first()

        result = StudyPlanController._map_plan(plan)
        if result:
            redis_instance.set_json(cache_key, serialize_data(
                result.model_dump()), expiry=1800)
        return result

    @staticmethod
    def get_study_plan_by_week(user_id: str, week_date: str):
        try:
            target_date = datetime.fromisoformat(week_date).date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        with CreateDBSession() as session:
            plan = session.query(StudyPlan).options(
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.course),
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.topic)
            ).filter(
                StudyPlan.user_id == UUID(user_id),
                StudyPlan.week_start_date == target_date
            ).first()

        if not plan:
            raise HTTPException(
                status_code=404, detail="No plan found for this week")
        return StudyPlanController._map_plan(plan)

    @staticmethod
    def update_strength(user_id: str, course_id: int, strength: int):
        with CreateDBSession() as session:
            existing = session.query(SubjectStrength).filter_by(
                user_id=UUID(user_id), course_id=course_id
            ).first()

            if existing:
                existing.strength = strength
            else:
                session.add(SubjectStrength(
                    user_id=UUID(user_id), course_id=course_id, strength=strength
                ))
            session.commit()
        return SuccessOut(message="Strength updated")

    @staticmethod
    def get_user_strengths(user_id: str):
        """Optimized strength fetching with joined course names."""
        with CreateDBSession() as session:
            strengths = session.query(SubjectStrength).options(
                joinedload(SubjectStrength.course)
            ).filter(SubjectStrength.user_id == UUID(user_id)).all()

            return [
                SubjectStrengthOut(
                    id=s.id,
                    course_id=s.course_id,
                    course_name=s.course.name,
                    strength=s.strength
                ) for s in strengths
            ]

    @staticmethod
    def swap_days(user_id: str, data):
        if StudyPlanService.swap_days(UUID(user_id), data.from_day, data.to_day):
            redis_instance.delete(f"user_current_week_plan:{user_id}")
            return SuccessOut(message="Days swapped successfully")
        raise HTTPException(status_code=400, detail="Swap failed")

    @staticmethod
    def delete_study_plan(user_id: str, plan_id: int):
        with CreateDBSession() as session:
            plan = session.query(StudyPlan).filter_by(
                id=plan_id, user_id=UUID(user_id)).first()
            if not plan:
                raise HTTPException(status_code=404, detail="Plan not found")
            session.delete(plan)
            session.commit()

        redis_instance.delete(f"user_current_week_plan:{user_id}")
        redis_instance.delete(f"user_study_plans:{user_id}")
        return SuccessOut(message="Study plan deleted successfully")

    @staticmethod
    def get_user_study_plans(user_id: str):
        """Fetches all plans for a user. Optimized with nested eager loading."""
        cache_key = f"user_study_plans:{user_id}"
        if cached := redis_instance.get_json(cache_key):
            return [StudyPlanOut(**p) for p in cached]

        with CreateDBSession() as session:
            # We fetch all plans and their daily sessions + courses/topics in ONE query
            plans = session.query(StudyPlan).options(
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.course),
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.topic)
            ).filter(StudyPlan.user_id == UUID(user_id)).all()

        # Use the centralized mapper for the entire list
        result = [StudyPlanController._map_plan(p) for p in plans]

        # Cache the serialized result
        redis_instance.set_json(
            cache_key,
            [serialize_data(r.model_dump()) for r in result],
            expiry=1800
        )
        return result

    @staticmethod
    def get_study_plan_by_id(user_id: str, plan_id: int):
        """Fetches a specific plan by ID, verifying ownership."""
        with CreateDBSession() as session:
            plan = session.query(StudyPlan).options(
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.course),
                joinedload(StudyPlan.daily_sessions).joinedload(
                    DailyStudySession.topic)
            ).filter(
                StudyPlan.id == plan_id,
                StudyPlan.user_id == UUID(user_id)
            ).first()

        if not plan:
            raise HTTPException(status_code=404, detail="Study plan not found")

        return StudyPlanController._map_plan(plan)
