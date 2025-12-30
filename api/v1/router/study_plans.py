import error
from fastapi import APIRouter, Depends
from controller.study_plans import StudyPlanController
from schema.study_plans import (
    StudyPlanGenerateIn, StudyPlanOut, StudyPlanSwapIn,
    SubjectStrengthOut
)
from schema import SuccessOut
from service.auth import verify_access_token

router = APIRouter(tags=["Study Plans"])


@router.post("/study-plans/generate", response_model=SuccessOut)
async def generate_study_plan(
    data: StudyPlanGenerateIn,
    auth_data: dict = Depends(verify_access_token)
):
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")
    return await StudyPlanController.generate_study_plan_async(user_id, data)


@router.get("/study-plans/current", response_model=StudyPlanOut)
async def get_current_week_plan(auth_data: dict = Depends(verify_access_token)):
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")
    result = await StudyPlanController.get_current_week_plan_async(user_id)
    if result is None:
        raise error.InvalidRequestError(
            "No study plan found for current week", 404)
    return result


@router.put("/study-plans/swap-days", response_model=SuccessOut)
async def swap_days(
    data: StudyPlanSwapIn,
    auth_data: dict = Depends(verify_access_token)
):
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")
    return await StudyPlanController.swap_days_async(user_id, data)


@router.get("/study-plans/strengths", response_model=list[SubjectStrengthOut])
async def get_user_strengths(auth_data: dict = Depends(verify_access_token)):
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")
    return await StudyPlanController.get_user_strengths_async(user_id)


@router.put("/study-plans/strengths/{course_id}/{strength}", response_model=SuccessOut)
async def update_strength(
    course_id: int,
    strength: int,
    auth_data: dict = Depends(verify_access_token)
):
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")
    return await StudyPlanController.update_strength_async(user_id, course_id, strength)


@router.get("/study-plans", response_model=list[StudyPlanOut])
async def get_user_study_plans(auth_data: dict = Depends(verify_access_token)):
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")
    return await StudyPlanController.get_user_study_plans_async(user_id)


@router.get("/study-plans/{plan_id}", response_model=StudyPlanOut)
async def get_study_plan_by_id(
    plan_id: int,
    auth_data: dict = Depends(verify_access_token)
):
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")
    return await StudyPlanController.get_study_plan_by_id_async(user_id, plan_id)


@router.delete("/study-plans/{plan_id}", response_model=SuccessOut)
async def delete_study_plan(
    plan_id: int,
    auth_data: dict = Depends(verify_access_token)
):
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")
    return await StudyPlanController.delete_study_plan_async(user_id, plan_id)


@router.get("/study-plans/week/{week_date}", response_model=StudyPlanOut)
async def get_study_plan_by_week(
    week_date: str,
    auth_data: dict = Depends(verify_access_token)
):
    user_id = auth_data.get("user_id")
    if not user_id:
        raise error.AuthenticationError("Invalid authentication token")
    return await StudyPlanController.get_study_plan_by_week_async(user_id, week_date)
