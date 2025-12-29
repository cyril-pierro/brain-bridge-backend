from fastapi import FastAPI, responses
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from fastapi import exceptions as exc
from sqlalchemy.exc import IntegrityError, DBAPIError
from api.v1.router import (
    user,
    teams,
    courses,
    quiz,
    flashcards,
    enrolment,
    hub,
    instructors,
    ai,
    reviews,
    study_plans,
)
from api.v1.router.support import support_router
from core.setup import Base, database
import handler as hlp
import secrets
from config.setting import settings
from error import ServerError

# Create database tables and indexes
Base.metadata.create_all(bind=database.get_engine)

# Add database indexes for better performance
from sqlalchemy import Index
from model.users import User
from model.subscription import Subscription
from model.enrolment import Enrolment
from model.topics import Topic
from model.topic_completion import UserTopicCompletion
from model.study_plans import DailyStudySession
from model.questions import QuizQuestion, Flashcard

# Create indexes on frequently queried columns
Index('idx_users_email', User.email).create(bind=database.get_engine, checkfirst=True)
Index('idx_users_role', User.role).create(bind=database.get_engine, checkfirst=True)
Index('idx_users_is_verified', User.is_verified).create(bind=database.get_engine, checkfirst=True)
Index('idx_users_created_at', User.created_at).create(bind=database.get_engine, checkfirst=True)

# Composite index for user authentication
Index('idx_users_email_verified', User.email, User.is_verified).create(bind=database.get_engine, checkfirst=True)

# Enrollment indexes for faster course lookups
Index('idx_enrolments_user_id', Enrolment.user_id).create(bind=database.get_engine, checkfirst=True)
Index('idx_enrolments_course_id', Enrolment.course_id).create(bind=database.get_engine, checkfirst=True)

# Topic indexes for course-topic relationships
Index('idx_topics_course_id', Topic.course_id).create(bind=database.get_engine, checkfirst=True)
Index('idx_topics_order', Topic.order).create(bind=database.get_engine, checkfirst=True)

# Study plan indexes
Index('idx_daily_sessions_plan_id', DailyStudySession.study_plan_id).create(bind=database.get_engine, checkfirst=True)
Index('idx_topic_completions_user_id', UserTopicCompletion.user_id).create(bind=database.get_engine, checkfirst=True)

# Content indexes
Index('idx_flashcards_course_id', Flashcard.course_id).create(bind=database.get_engine, checkfirst=True)
Index('idx_quiz_questions_course_id', QuizQuestion.course_id).create(bind=database.get_engine, checkfirst=True)

app = FastAPI(
    title="Brain Bridge API", version="1.0.0", description="Learning System For Schools"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))

# Add GZip compression for better performance
app.add_middleware(GZipMiddleware, minimum_size=1000)


app.add_exception_handler(ValueError, hlp.value_error_handler)
app.add_exception_handler(ValidationError, hlp.validation_error_handler)
app.add_exception_handler(RequestValidationError, hlp.validation_error_handler)
app.add_exception_handler(exc.HTTPException, hlp.validation_http_exceptions_handler)
app.add_exception_handler(IntegrityError, hlp.db_error_handler)
app.add_exception_handler(DBAPIError, hlp.db_error_handler)
app.add_exception_handler(ServerError, hlp.server_error_handler)


app.include_router(user, prefix=settings.API_PREFIX)
app.include_router(teams, prefix=settings.API_PREFIX)
app.include_router(courses, prefix=settings.API_PREFIX)
app.include_router(quiz, prefix=settings.API_PREFIX)
app.include_router(flashcards, prefix=settings.API_PREFIX)
app.include_router(enrolment, prefix=settings.API_PREFIX)
app.include_router(hub, prefix=settings.API_PREFIX)
app.include_router(instructors, prefix=settings.API_PREFIX)
app.include_router(ai, prefix=settings.API_PREFIX)
app.include_router(reviews, prefix=settings.API_PREFIX)
app.include_router(study_plans, prefix=settings.API_PREFIX)
app.include_router(support_router, prefix=settings.API_PREFIX)


@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return responses.RedirectResponse("/docs")
