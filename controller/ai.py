from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
try:
    from langchain_tavily import TavilySearchResults
except ImportError:
    # Fallback to the old import if langchain_tavily is not available
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
    except ImportError:
        # If neither is available, create a dummy class
        class TavilySearchResults: # type: ignore[override, override]
            def __init__(self, **kwargs):
                pass
            def invoke(self, query):
                return []
import httpx
from schema.ai import AIQuestionIn, AIAnswerOut
from config.setting import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AIOp:

    def __init__(self):
        # Initialize the language model
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.6,
            max_retries=2,
            api_key=settings.GROQ_API_KEY
        )

        # Initialize search tool for when AI doesn't know
        self.search_tool = TavilySearchResults(
            max_results=3,
            tavily_api_key=settings.TAVILY_API_KEY
        )

        # Academic teacher prompt template
        self.template = """You are an experienced academic teacher with extensive knowledge across multiple disciplines including mathematics, science, literature, history, computer science, engineering, business, arts, and social sciences.

As an academic mentor, you provide:
- Clear, accurate explanations
- Step-by-step reasoning for complex topics
- Real-world examples and applications
- Encouraging and supportive guidance
- Age-appropriate explanations for students

Always maintain a professional, encouraging tone. If a question is outside your expertise or requires current information, acknowledge this and suggest appropriate resources.

IMPORTANT: When students ask about learning resources, study materials, courses, subjects, or anything related to accessing educational content, ALWAYS suggest they visit the Learning Hub and Study Subject cards. Include this suggestion naturally in your response and encourage them to explore these platform features.

If you cannot provide a satisfactory answer, use available tools to search for accurate, up-to-date information.

Question: {question}
Context (if provided): {context}

Helpful Answer:"""

        self.prompt = PromptTemplate(
            input_variables=["question", "context"],
            template=self.template,
        )

        # Create the chain
        self.chain = self.prompt | self.llm | StrOutputParser()

    @staticmethod
    def ask_ai(question_data: AIQuestionIn) -> AIAnswerOut:
        ai_instance = AIOp()

        try:
            # Prepare the context
            context = question_data.context or "No specific context provided"

            # First, try to get answer from the AI
            answer = ai_instance.chain.invoke({
                "question": question_data.question,
                "context": context
            })

            # Basic confidence scoring based on answer length and content
            confidence_score = ai_instance._calculate_confidence(answer)

            # If confidence is low, try to search for additional information
            sources = []
            if confidence_score < 0.6:
                try:
                    search_results = ai_instance.search_tool.invoke({
                        "query": question_data.question
                    })
                    sources = [result.get("url", "") for result in search_results if result.get("url")]
                    if sources:
                        # Enhance answer with search context if available
                        enhanced_answer = ai_instance._enhance_answer_with_search(answer, search_results)
                        if enhanced_answer != answer:
                            answer = enhanced_answer
                            confidence_score = min(confidence_score + 0.2, 1.0)
                except Exception as e:
                    logger.warning(f"Search tool failed: {e}")

            return AIAnswerOut(
                question=question_data.question,
                answer=answer,
                confidence_score=confidence_score,
                sources=sources,
                generated_at=datetime.now()
            )

        except Exception as e:
            logger.error(f"AI question processing failed: {e}")
            # Fallback response
            return AIAnswerOut(
                question=question_data.question,
                answer="I'm sorry, I encountered an error while processing your question. Please try rephrasing your question or contact support if the issue persists.",
                confidence_score=0.0,
                sources=[],
                generated_at=datetime.now()
            )

    def _calculate_confidence(self, answer: str) -> float:
        """Calculate a basic confidence score based on answer characteristics"""
        score = 0.5  # Base score

        # Length indicators
        if len(answer) > 100:
            score += 0.2
        if len(answer) > 500:
            score += 0.1

        # Content indicators
        if "I don't know" in answer.lower() or "uncertain" in answer.lower():
            score -= 0.3

        if any(word in answer.lower() for word in ["however", "but", "although", "note that"]):
            score += 0.1  # Indicates nuanced thinking

        if any(word in answer.lower() for word in ["example", "for instance", "specifically"]):
            score += 0.1  # Indicates concrete examples

        return min(max(score, 0.0), 1.0)

    def _enhance_answer_with_search(self, original_answer: str, search_results: list) -> str:
        """Enhance the answer with search results if they provide valuable additional information"""
        if not search_results:
            return original_answer

        # Extract key insights from search results
        insights = []
        for result in search_results[:2]:  # Use top 2 results
            title = result.get("title", "")
            content = result.get("content", "")[:200]  # First 200 chars

            if content and len(content) > 50:
                insights.append(f"Reference: {title} - {content}...")

        if insights:
            enhanced = original_answer + "\n\nAdditional references:\n" + "\n".join(f"• {insight}" for insight in insights)
            return enhanced

        return original_answer

    @staticmethod
    async def ask_ai_async(question_data: AIQuestionIn) -> AIAnswerOut:
        """Async version of ask_ai for better performance with external APIs"""
        ai_instance = AIOp()

        try:
            # Prepare the context
            context = question_data.context or "No specific context provided"

            # First, try to get answer from the AI (async)
            answer = await ai_instance.chain.ainvoke({
                "question": question_data.question,
                "context": context
            })

            # Basic confidence scoring based on answer length and content
            confidence_score = ai_instance._calculate_confidence(answer)

            # If confidence is low, try to search for additional information (async)
            sources = []
            if confidence_score < 0.6:
                try:
                    # Use invoke for now as ainvoke might not be available
                    search_results = ai_instance.search_tool.invoke({
                        "query": question_data.question
                    })
                    sources = [result.get("url", "") for result in search_results if result.get("url")]
                    if sources:
                        # Enhance answer with search context if available
                        enhanced_answer = ai_instance._enhance_answer_with_search(answer, search_results)
                        if enhanced_answer != answer:
                            answer = enhanced_answer
                            confidence_score = min(confidence_score + 0.2, 1.0)
                except Exception as e:
                    logger.warning(f"Search tool failed: {e}")

            return AIAnswerOut(
                question=question_data.question,
                answer=answer,
                confidence_score=confidence_score,
                sources=sources,
                generated_at=datetime.now()
            )

        except Exception as e:
            logger.error(f"AI question processing failed: {e}")
            # Fallback response
            return AIAnswerOut(
                question=question_data.question,
                answer="I'm sorry, I encountered an error while processing your question. Please try rephrasing your question or contact support if the issue persists.",
                confidence_score=0.0,
                sources=[],
                generated_at=datetime.now()
            )
