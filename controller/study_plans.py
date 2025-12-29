from fastapi import HTTPException
from schema.study_plans import (
    StudyPlanGenerateIn,
    SubjectStrengthOut, StudyPlanSwapIn,
    StudyPlanOut,
    DailyStudySessionOut,
    TaskOut
)
from service.study_plans import StudyPlanService
from model.study_plans import SubjectStrength, StudyPlan
from schema import SuccessOut
from uuid import UUID
from service.redis import Redis
from util.serialize import serialize_data

redis_instance = Redis()


class StudyPlanController:
    @staticmethod
    def generate_study_plan(user_id: str, data: StudyPlanGenerateIn):
        try:
            plan = StudyPlanService.generate_study_plan(UUID(user_id), data)
            # Invalidate caches
            redis_instance.delete(f"user_current_week_plan:{user_id}")
            redis_instance.delete(f"user_study_plans:{user_id}")
            return {"message": "Study plan generated successfully", "plan_id": plan.id}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    def get_current_week_plan(user_id: str):
        # Try to get from cache first
        cache_key = f"user_current_week_plan:{user_id}"
        cached_result = redis_instance.get_json(cache_key)
        if cached_result:
            try:
                # Convert cached data back to Pydantic models
                daily_sessions = [
                    DailyStudySessionOut(**session) for session in cached_result["daily_sessions"]
                ]
                return StudyPlanOut(
                    id=cached_result["id"],
                    user_id=cached_result["user_id"],
                    week_start_date=cached_result["week_start_date"],
                    daily_sessions=daily_sessions
                )
            except Exception:
                # If cache data is corrupted, ignore and fetch from db
                pass

        result = StudyPlanService.get_current_week_plan(UUID(user_id))
        if not result:
            raise HTTPException(status_code=404, detail="No study plan for current week")

        # Cache the result for 30 minutes
        serialized_data = serialize_data(result.model_dump())
        redis_instance.set_json(cache_key, serialized_data, expiry=1800)

        return result

    @staticmethod
    def swap_days(user_id: str, data: StudyPlanSwapIn):
        success = StudyPlanService.swap_days(UUID(user_id), data.from_day, data.to_day)
        if not success:
            raise HTTPException(status_code=400, detail="Swap failed")
        # Invalidate caches
        redis_instance.delete(f"user_current_week_plan:{user_id}")
        redis_instance.delete(f"user_study_plans:{user_id}")
        return SuccessOut(message="Days swapped successfully")

    @staticmethod
    def get_user_strengths(user_id: str):
        strengths = SubjectStrength.get_user_strengths(UUID(user_id))
        return [
            SubjectStrengthOut(
                id=s.id,
                course_id=s.course_id,
                course_name=s.course.name,
                strength=s.strength
            ) for s in strengths
        ]

    @staticmethod
    def update_strength(user_id: str, course_id: int, strength: int):
        existing = SubjectStrength.get_strength(UUID(user_id), course_id)
        if existing:
            existing.strength = strength
            existing.save()
        else:
            new_strength = SubjectStrength(
                user_id=UUID(user_id),
                course_id=course_id,
                strength=strength
            )
            new_strength.save()
        return SuccessOut(message="Strength updated")

    @staticmethod
    def get_user_study_plans(user_id: str):
        # Try to get from cache first
        cache_key = f"user_study_plans:{user_id}"
        cached_result = redis_instance.get_json(cache_key)
        if cached_result:
            try:
                # Convert cached data back to Pydantic models
                result = []
                for plan_data in cached_result:
                    daily_sessions = [
                        DailyStudySessionOut(**session) for session in plan_data["daily_sessions"]
                    ]
                    result.append(StudyPlanOut(
                        id=plan_data["id"],
                        user_id=plan_data["user_id"],
                        week_start_date=plan_data["week_start_date"],
                        daily_sessions=daily_sessions
                    ))
                return result
            except Exception:
                # If cache data is corrupted, ignore and fetch from db
                pass

        try:
            plans = StudyPlan.get_user_study_plans(UUID(user_id))
        except Exception:
            plans = []

        result = []
        for plan in plans:
            # Build daily sessions for each plan
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

            study_plan_out = StudyPlanOut(
                id=plan.id,
                user_id=str(plan.user_id),
                week_start_date=plan.week_start_date,
                daily_sessions=daily_sessions
            )
            result.append(study_plan_out)

        # Cache the result for 30 minutes
        serialized_data = [serialize_data(plan.model_dump()) for plan in result]
        redis_instance.set_json(cache_key, serialized_data, expiry=1800)

        return result

    @staticmethod
    def get_study_plan_by_id(user_id: str, plan_id: int):
        plan = StudyPlan.get_study_plan_by_id(plan_id)
        if not plan or str(plan.user_id) != user_id:
            raise HTTPException(status_code=404, detail="Study plan not found")

        # Build daily sessions
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
    def delete_study_plan(user_id: str, plan_id: int):
        plan = StudyPlan.get_study_plan_by_id(plan_id)
        if not plan or str(plan.user_id) != user_id:
            raise HTTPException(status_code=404, detail="Study plan not found")

        success = plan.delete()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete study plan")

        # Invalidate caches
        redis_instance.delete(f"user_current_week_plan:{user_id}")
        redis_instance.delete(f"user_study_plans:{user_id}")

        return SuccessOut(message="Study plan deleted successfully")

    @staticmethod
    def get_study_plan_by_week(user_id: str, week_date: str):
        from datetime import datetime

        try:
            # Parse the week date
            week_start = datetime.fromisoformat(week_date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        plan = StudyPlan.get_current_week_plan(UUID(user_id), week_start)
        if not plan:
            raise HTTPException(status_code=404, detail="No study plan found for specified week")

        # Build daily sessions
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
