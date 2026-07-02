"""
LLM Service — Abstraction Layer

This is the ONLY module in the entire codebase that knows about Gemini.
All AI agents must call get_llm() to obtain an LLM instance.

This abstraction means we can swap Gemini for OpenAI, Anthropic, or any
other provider in the future by changing only this file.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings


def get_llm(temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    """
    Factory function that returns a configured Gemini LLM instance.

    Args:
        temperature: Controls randomness. 0.1 is near-deterministic,
                     which is ideal for structured code analysis.

    Returns:
        A configured ChatGoogleGenerativeAI instance ready for use.
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file and Render environment variables."
        )

    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
    )
