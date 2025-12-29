from model.instructors import Instructor
from model.bookings import InstructorBooking
from model.instructors_specialty import InstructorCourseSpecialty
from schema.instructors import InstructorIn, InstructorBookingIn
from model.users import User, pwd_hasher
from util.gen import generate_temporary_password
from util.meeting import MeetingUtils
from service.email import MailService
from service.auth import TokenManager
import error
from util.enum import BookingStatus, BookingType
from core.db import CreateDBSession
from config.setting import settings
from datetime import datetime, timedelta


class InstructorOp:

    @staticmethod
    def add_instructor(data: InstructorIn) -> Instructor:
        # Create user first
        new_data = {
            "email": data.user.email,
            "full_name": f"{data.user.first_name}-{data.user.last_name}",
            "role": "instructor",
            "gender": data.user.gender,
            "hashed_password": pwd_hasher.hash(generate_temporary_password()),
        }
        user = User.create(new_data)
        # Create instructor with user id
        new_instructor = Instructor.add_instructor(
            {
                "id": user.id,
                "location": data.location,
                "phone_number": data.phone_number,
                "years_of_experience": data.years_of_experience,
                "hourly_rate": data.hourly_rate,
                "expertise_field": data.expertise_field,
            }
        )
        # Add specialties
        for course_id in data.specialties:
            InstructorCourseSpecialty.add(user.id, course_id)
        return new_instructor

    @staticmethod
    def verify_instructor(instructor_id: int) -> Instructor:
        instructor = User.get_user_by_id(instructor_id)
        if not instructor:
            raise error.ResourceNotFoundError("Instructor not found")
        return instructor.update(**{"is_verified": True})

    @staticmethod
    def get_instructor(user_id: int) -> Instructor:
        instructor = Instructor.get_instructor_by_user_id(user_id)
        if not instructor:
            raise error.ResourceNotFoundError("Instructor not found")
        return instructor

    @staticmethod
    def get_all_instructors() -> list[Instructor]:
        return Instructor.get_all_instructors()

    @staticmethod
    def get_available_instructors() -> list[Instructor]:
        from model.users import User
        with CreateDBSession() as db:
            instructors = db.query(Instructor).join(
                User).filter(User.is_verified == True).all()
            return instructors

    @staticmethod
    def update_instructor(user_id: int, data: InstructorIn) -> Instructor:
        updated_instructor = InstructorOp.get_instructor(user_id)
        user_updated = User.get_user_by_id(user_id).update(
            **{
                "full_name": f"{data.user.first_name}-{data.user.last_name}",
                "gender": data.user.gender,
            }
        )

        updated_instructor.update(
            {
                "location": data.location,
                "phone_number": data.phone_number,
                "years_of_experience": data.years_of_experience,
                "hourly_rate": data.hourly_rate,
                "expertise_field": data.expertise_field,
            }
        )
        if data.specialties:
            InstructorCourseSpecialty.delete_all_specialties_of_instructor(
                user_updated.id
            )
        for course_id in data.specialties:
            InstructorCourseSpecialty.add(user_updated.id, course_id)
        return updated_instructor

    @staticmethod
    def delete_instructor(user_id: int) -> bool:
        instructor = InstructorOp.get_instructor(user_id)
        return instructor.delete()

    @staticmethod
    def add_instructor_specialty(
        user_id: int, course_id: int
    ) -> InstructorCourseSpecialty:
        return InstructorCourseSpecialty.add(user_id, course_id)

    @staticmethod
    def get_instructor_specialties(user_id: int) -> list[InstructorCourseSpecialty]:
        return InstructorCourseSpecialty.get_specialties_for_instructor(user_id)

    @staticmethod
    def delete_instructor_specialty(
        user_id: int, course_id: int
    ) -> InstructorCourseSpecialty:
        specialty = InstructorCourseSpecialty.get_specialty_for_instructor(
            user_id, course_id
        )
        if not specialty:
            raise error.ResourceNotFoundError("Specialty not found")
        return specialty.delete()

    @staticmethod
    def book_instructor(
        user_id: int, instructor_id: int, data: InstructorBookingIn, background_tasks
    ) -> InstructorBooking:
        value = {
            "user_id": user_id,
            "instructor_id": instructor_id,
            **data.model_dump(),
        }
        new_booking = InstructorBooking.add(value)

        # Send email to tutor for online bookings
        if data.booking_type == BookingType.online:
            background_tasks.add_task(
                InstructorOp._send_tutor_confirmation_email, new_booking)

        return new_booking

    @staticmethod
    def cancel_book_session(
        instructor_id: str, book_session_id: int, for_tutor: bool = False
    ) -> InstructorBooking:
        session_found = InstructorBooking.get_booking_session(book_session_id)
        if not session_found:
            raise error.ResourceNotFoundError("Book session not found")

        if session_found.status != BookingStatus.pending.value:
            raise error.InvalidRequestError("Book session already processed")

        check_id = str(
            session_found.instructor_id if for_tutor else session_found.user_id)
        if check_id != instructor_id:
            raise error.InvalidRequestError(
                "You cannot perform action on this record")

        return session_found.update(status=BookingStatus.cancelled.value)

    @staticmethod
    def reschedule_book_session(
        user_id: str, book_session_id: int, data: InstructorBookingIn, background_tasks
    ) -> InstructorBooking:
        session_found = InstructorBooking.get_booking_session(book_session_id)
        if not session_found:
            raise error.ResourceNotFoundError("Book session not found")
        if session_found.status != BookingStatus.pending.value:
            raise error.InvalidRequestError(
                "Only pending sessions can be rescheduled")
        if str(session_found.user_id) != user_id:
            raise error.InvalidRequestError(
                "You cannot perform action on this record")

        # Update the booking with new data
        update_data = data.model_dump()
        rescheduled_booking = session_found.update(**update_data)

        # Send email notification to tutor about rescheduling
        background_tasks.add_task(
            InstructorOp._send_reschedule_notification_email, rescheduled_booking)

        return rescheduled_booking

    @staticmethod
    def confirm_book_session(
        instructor_id: str, book_session_id: int, background_tasks
    ) -> InstructorBooking:
        session_found = InstructorBooking.get_booking_session(book_session_id)
        if not session_found:
            raise error.ResourceNotFoundError("Book session not found")
        if session_found.status != BookingStatus.pending.value:
            raise error.InvalidRequestError("Book session already processed")
        if str(session_found.instructor_id) != instructor_id:
            raise error.InvalidRequestError(
                "You cannot perform action on this record")

        # Generate meeting link for online bookings
        meeting_link = None
        if session_found.booking_type == BookingType.online:
            # Get attendee emails (student and instructor)
            student = session_found.user
            instructor_user = User.get_user_by_id(
                str(session_found.instructor_id))

            if student and instructor_user:
                meeting_link = MeetingUtils.get_meeting_link(
                    booking_type=session_found.booking_type.value,
                    attendee_emails=[student.email, instructor_user.email],
                    start_datetime=session_found.scheduled_datetime,
                    duration_hours=session_found.duration_hours
                )

        # Update booking with confirmed status and meeting link
        update_data = {"status": BookingStatus.confirmed.value}
        if meeting_link:
            update_data["meeting_link"] = meeting_link

        confirmed_booking = session_found.update(**update_data)

        # Send confirmation emails using background tasks
        background_tasks.add_task(
            InstructorOp._send_confirmation_emails, confirmed_booking)

        return confirmed_booking

    @staticmethod
    def complete_book_session(
        book_session_id: int, background_tasks
    ) -> InstructorBooking:
        session_found = InstructorBooking.get_booking_session(book_session_id)
        if not session_found:
            raise error.ResourceNotFoundError("Book session not found")
        if session_found.status != BookingStatus.confirmed.value:
            raise error.InvalidRequestError("Book session is not confirmed")
        # Check if session is over (current time > scheduled_datetime + duration_hours)
        session_end_time = session_found.scheduled_datetime + \
            timedelta(hours=session_found.duration_hours)
        current_time = datetime.utcnow()

        if current_time < session_end_time:
            raise error.InvalidRequestError(
                "Session is not yet completed. Please wait until the session ends.")
        # Mark as completed
        completed_booking = session_found.update(
            **{"status": BookingStatus.completed.value})

        # Send email notification to tutor
        background_tasks.add_task(
            InstructorOp._send_session_completion_email, completed_booking)

        return completed_booking

    @staticmethod
    def get_student_bookings(user_id: str) -> list[InstructorBooking]:
        """Get all bookings for a student."""
        return InstructorBooking.get_bookings_for_student(user_id)

    @staticmethod
    async def _send_tutor_confirmation_email(booking: InstructorBooking):
        """Send confirmation request email to tutor for online bookings."""
        try:
            # Get instructor user details
            instructor_user = User.get_user_by_id(str(booking.instructor_id))
            if not instructor_user:
                return

            # Get student details
            student = booking.user

            # Format datetime
            session_datetime = booking.scheduled_datetime.strftime(
                "%B %d, %Y at %I:%M %p")

            # Generate secure token for tutor confirmation (expires in 7 days)
            token_data = {
                "booking_id": booking.id,
                "instructor_id": str(booking.instructor_id),
                "action": "confirm_booking"
            }
            token = TokenManager.create_access_token(
                token_data, expires_in_minutes=10080)  # 7 days

            # Generate URLs for confirm/cancel actions with token
            confirm_url = f"{settings.REDIRECT_URI_BASE}{settings.API_PREFIX}/book/{booking.id}/email/confirm?token={token}"
            cancel_url = f"{settings.REDIRECT_URI_BASE}{settings.API_PREFIX}/book/{booking.id}/email/cancel?token={token}"

            email_content = {
                "instructor_name": instructor_user.full_name.replace("-", " "),
                "student_name": student.full_name.replace("-", " ") if student.full_name else f"{student.first_name} {student.last_name}",
                "student_email": student.email,
                "session_datetime": session_datetime,
                "booking_type": booking.booking_type.value,
                "duration_hours": booking.duration_hours,
                "confirm_url": confirm_url,
                "cancel_url": cancel_url,
            }

            await MailService.send_email(
                email=instructor_user.email,
                subject="New Tutoring Session Request - Action Required",
                content=email_content,
                email_template="tutor_booking_confirmation.html"
            )
        except Exception as e:
            print(f"Failed to send tutor confirmation email: {str(e)}")

    @staticmethod
    async def _send_confirmation_emails(booking: InstructorBooking):
        """Send confirmation emails to both student and tutor."""
        try:
            # Get student and instructor details
            student = booking.user
            instructor_user = User.get_user_by_id(str(booking.instructor_id))
            if not student or not instructor_user:
                return

            # Format datetime
            session_datetime = booking.scheduled_datetime.strftime(
                "%B %d, %Y at %I:%M %p")

            email_content = {
                "instructor_name": instructor_user.full_name.replace("-", " "),
                "instructor_email": instructor_user.email,
                "student_name": student.full_name.replace("-", " ") if student.full_name else f"{student.first_name} {student.last_name}",
                "session_datetime": session_datetime,
                "booking_type": booking.booking_type.value,
                "duration_hours": booking.duration_hours,
                "meeting_link": booking.meeting_link or "To be provided",
            }

            # Send email to student
            await MailService.send_email(
                email=student.email,
                subject="Your Tutoring Session is Confirmed!",
                content=email_content,
                email_template="student_booking_confirmed.html"
            )

            # Send email to tutor (could use a different template or same)
            await MailService.send_email(
                email=instructor_user.email,
                subject="Tutoring Session Confirmed - Meeting Details",
                content=email_content,
                email_template="student_booking_confirmed.html"  # Reuse template
            )
        except Exception as e:
            print(f"Failed to send confirmation emails: {str(e)}")

    @staticmethod
    async def _send_reschedule_notification_email(booking: InstructorBooking):
        """Send reschedule notification email to tutor."""
        try:
            # Get student and instructor details
            student = booking.user
            instructor_user = User.get_user_by_id(str(booking.instructor_id))
            if not student or not instructor_user:
                return

            # Format datetime
            session_datetime = booking.scheduled_datetime.strftime(
                "%B %d, %Y at %I:%M %p")

            email_content = {
                "instructor_name": instructor_user.full_name.replace("-", " "),
                "student_name": student.full_name.replace("-", " ") if student.full_name else f"{student.first_name} {student.last_name}",
                "student_email": student.email,
                "session_datetime": session_datetime,
                "booking_type": booking.booking_type.value,
                "duration_hours": booking.duration_hours,
            }

            # Send email to tutor
            await MailService.send_email(
                email=instructor_user.email,
                subject="Tutoring Session Rescheduled",
                content=email_content,
                email_template="session_rescheduled_notification.html"
            )
        except Exception as e:
            print(f"Failed to send reschedule notification email: {str(e)}")

    @staticmethod
    async def _send_session_completion_email(booking: InstructorBooking):
        """Send session completion notification email to tutor."""
        try:
            # Get student and instructor details
            student = booking.user
            instructor_user = User.get_user_by_id(str(booking.instructor_id))
            if not student or not instructor_user:
                return

            # Format datetime
            session_datetime = booking.scheduled_datetime.strftime(
                "%B %d, %Y at %I:%M %p")

            email_content = {
                "student_name": student.full_name.replace("-", " ") if student.full_name else f"{student.first_name} {student.last_name}",
                "student_email": student.email,
                "session_datetime": session_datetime,
                "booking_type": booking.booking_type.value,
                "duration_hours": booking.duration_hours,
            }

            # Send email to tutor
            await MailService.send_email(
                email=instructor_user.email,
                subject="Session Completed - Student Confirmation Received",
                content=email_content,
                email_template="session_completed_notification.html"
            )
        except Exception as e:
            print(f"Failed to send session completion email: {str(e)}")
