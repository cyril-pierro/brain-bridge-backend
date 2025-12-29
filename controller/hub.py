from model.hub import VideoResource, VideoLike
from model.enrolment import Enrolment
from schema.hub import LearningHubIn
from controller.enrolments import EnrolmentOp


class LearningHubOp:
    @staticmethod
    def add_video(topic_id: int, data: LearningHubIn) -> VideoResource:
        video = VideoResource.add(topic_id=topic_id, **data.model_dump())
        return video

    @staticmethod
    def get_video(video_id: int) -> VideoResource:
        video = VideoResource.validate_video(video_id)
        return video

    @staticmethod
    def update_video(video_id: int, data: LearningHubIn) -> VideoResource:
        video = VideoResource.validate_video(video_id)
        return video.update(**data.model_dump())

    @staticmethod
    def delete_video(video_id: int) -> bool:
        video = VideoResource.validate_video(video_id)
        return video.delete()

    @staticmethod
    def get_all_videos_for_courses_enroled(user_id: str) -> list[dict]:
        """Get all videos for enrolled courses with like status included."""
        from model.hub import VideoLike

        # Get enrollments
        enrollments = EnrolmentOp.get_courses_enroled_by_student(user_id=user_id)

        # Flatten videos and add like status
        videos_with_likes = []
        for enrolment in enrollments:
            if enrolment.course and enrolment.course.topics:
                for topic in enrolment.course.topics:
                    if topic.video_resources:
                        for video in topic.video_resources:
                            # Get like status for this video
                            existing_like = VideoLike.get_by_user_and_video(user_id, video.id)
                            liked = existing_like is not None

                            # Get like count
                            likes_count = VideoLike.get_video_likes_count(video.id)

                            videos_with_likes.append({
                                "id": video.id,
                                "title": video.title,
                                "youtube_url": video.youtube_url,
                                "duration_seconds": video.duration_seconds,
                                "liked": liked,
                                "likes_count": likes_count,
                                "topic": {
                                    "id": topic.id,
                                    "subject": topic.subject,
                                    "course": {
                                        "id": enrolment.course.id,
                                        "name": enrolment.course.name
                                    }
                                },
                                "course": {
                                    "id": enrolment.course.id,
                                    "name": enrolment.course.name
                                }
                            })

        return videos_with_likes

    @staticmethod
    def toggle_like(user_id: str, video_id: int) -> dict:
        """Toggle like status for a video. Returns like status and count."""
        # Validate video exists
        VideoResource.validate_video(video_id)

        # Check if user already liked this video
        existing_like = VideoLike.get_by_user_and_video(user_id, video_id)

        if existing_like:
            # Unlike: delete the like
            existing_like.delete()
            liked = False
        else:
            # Like: create new like
            like = VideoLike(user_id=user_id, video_id=video_id)
            like.save()
            liked = True

        # Get updated like count
        likes_count = VideoLike.get_video_likes_count(video_id)

        return {
            "liked": liked,
            "likes_count": likes_count
        }

    @staticmethod
    def get_like_status(user_id: str, video_id: int) -> dict:
        """Get like status and count for a video."""
        # Validate video exists
        VideoResource.validate_video(video_id)

        # Check if user liked this video
        existing_like = VideoLike.get_by_user_and_video(user_id, video_id)
        liked = existing_like is not None

        # Get like count
        likes_count = VideoLike.get_video_likes_count(video_id)

        return {
            "liked": liked,
            "likes_count": likes_count
        }
