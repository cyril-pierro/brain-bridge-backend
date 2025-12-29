from model.courses import Course
from model.topics import Topic
from model.topic_completion import UserTopicCompletion
from schema.courses import CourseIn, TopicIn


class CourseOp:
    @staticmethod
    def add(course_data: CourseIn) -> Course:
        return Course.add(course_data)

    @staticmethod
    def update(course_id: int, course_data: CourseIn) -> Course:
        return Course.update(course_id, course_data)

    @staticmethod
    def delete(course_id: int) -> bool:
        course = Course.validate_course(course_id)
        return course.delete()

    @staticmethod
    def get_courses() -> list[Course]:
        return Course.get_courses()

    @staticmethod
    def get_course_by_id(course_id: int) -> Course:
        return Course.validate_course(course_id)

    @staticmethod
    def add_topic(course_id: int, topic_data: TopicIn) -> Topic:
        Course.validate_course(course_id)
        return Topic.add(course_id, **topic_data.model_dump())

    @staticmethod
    def update_topic(topic_id: int, topic_data: TopicIn) -> Topic:
        topic_found = Topic.validate_topic(topic_id)
        return topic_found.update(**topic_data.model_dump())

    @staticmethod
    def delete_topic(topic_id: int) -> bool:
        topic_found = Topic.validate_topic(topic_id)
        return topic_found.delete()

    @staticmethod
    def get_topics(course_id: int) -> list[Topic]:
        Course.validate_course(course_id)
        return Topic.get_topics_by_course(course_id)

    @staticmethod
    def get_user_topics_completed(user_id: int) -> list[UserTopicCompletion]:
        return UserTopicCompletion.get_user_completions(user_id)

    @staticmethod
    def mark_topic_as_complete(user_id: int, topic_id: int) -> UserTopicCompletion:
        return UserTopicCompletion.mark_topic_as_complete(user_id, topic_id)
