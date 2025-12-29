from model.enrolment import Enrolment


class EnrolmentOp:
    @staticmethod
    def enroll_a_student(user_id: str, course_id: int) -> Enrolment:
        # Check current enrollments count to enforce 8 course limit
        current_enrollments = Enrolment.get_courses_enroled_by_user(user_id)
        if len(current_enrollments) >= 8:
            from error import InvalidRequestError
            raise InvalidRequestError(msg="Maximum 8 courses allowed per student", status_code=400)

        enrolment = Enrolment.create_enrolment(user_id=user_id, course_id=course_id)
        return enrolment

    @staticmethod
    def get_courses_enroled_by_student(user_id: str) -> list[Enrolment]:
        return Enrolment.get_courses_enroled_by_user(user_id)

    @staticmethod
    def get_enrolment_by_id(enrolment_id: int) -> Enrolment:
        enrolment = Enrolment.validate_enrolment(enrolment_id)
        return enrolment

    @staticmethod
    def unenroll_a_student(enrolment_id: int) -> bool:
        enrolment = Enrolment.validate_enrolment(enrolment_id)
        return enrolment.delete()
