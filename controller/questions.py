from model.questions import QuizQuestion, QuizAnswer, Flashcard
from schema.questions import QuizAnswerIn, QuizQuestionIn, FlashcardIn


class QuestionOp:

    @staticmethod
    def add_flashcard(course_id: int, flashcard_data: FlashcardIn) -> Flashcard:
        flashcard = Flashcard(course_id=course_id, **flashcard_data.model_dump())
        return flashcard.save()

    @staticmethod
    def get_flashcards(course_id: int, limit: int = 10) -> list[Flashcard]:
        return Flashcard.get_questions(course_id=course_id, limit=limit)

    @staticmethod
    def update_flashcard(flashcard_id: int, flashcard_data: FlashcardIn) -> Flashcard:
        flashcard = Flashcard.get(flashcard_id)
        return flashcard.update(**flashcard_data.model_dump())

    @staticmethod
    def delete_flashcard(flashcard_id: int) -> bool:
        flashcard = Flashcard.get(flashcard_id)
        return flashcard.delete()

    @staticmethod
    def add_quiz_question(course_id: int, quiz_data: QuizQuestionIn) -> QuizQuestion:
        question = QuizQuestion(
            course_id=course_id, question_text=quiz_data.question_text
        )
        question_created = question.save()
        if quiz_data.answers:
            for value in quiz_data.answers:
                answer_created = QuizAnswer(
                    question_id=question_created.id,
                    answer_text=value.answer_text,
                    is_correct=value.is_correct,
                )
                answer_created.save()
        return question_created

    @staticmethod
    def update_quiz_question(
        question_id: int, quiz_data: QuizQuestionIn
    ) -> QuizQuestion:
        # Get the question
        question = QuizQuestion.get(question_id)

        # Update question text
        question = question.update(question_text=quiz_data.question_text)

        # Delete existing answers
        QuizAnswer.delete_all_answers(question_id)
        # Create new answers
        if quiz_data.answers:
            for value in quiz_data.answers:
                answer = QuizAnswer(
                    question_id=question_id,
                    answer_text=value.answer_text,
                    is_correct=value.is_correct,
                )
                answer.save()

        return question

    @staticmethod
    def delete_quiz_question(question_id: int) -> bool:
        question = QuizQuestion.get(question_id)
        return question.delete()

    @staticmethod
    def get_quiz_questions(course_id: int, limit: int = 10) -> list[QuizQuestion]:
        return QuizQuestion.get_quiz_questions(course_id=course_id, limit=limit)

    @staticmethod
    def add_quiz_answer(question_id: int, answer_data: QuizAnswerIn) -> QuizAnswer:
        answer = QuizAnswer(question_id=question_id, **answer_data.model_dump())
        return answer.save()

    @staticmethod
    def update_quiz_answer(answer_id: int, answer_data: QuizAnswerIn) -> QuizAnswer:
        answer = QuizAnswer.get(answer_id)
        return answer.update(**answer_data.model_dump())

    @staticmethod
    def delete_quiz_answer(answer_id: int) -> bool:
        answer = QuizAnswer.get(answer_id)
        return answer.delete()

    @staticmethod
    def get_quiz_answers(question_id: int) -> list[QuizAnswer]:
        answer = QuizAnswer.get(question_id)
        return answer
