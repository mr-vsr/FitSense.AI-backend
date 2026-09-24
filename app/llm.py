import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

PRIMARY_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def get_chat_model(**kwargs):
    """Return the configured chat provider.

    Set LLM_PROVIDER=openai to use OpenAI directly.
    Otherwise Gemini is used.
    """
    if PRIMARY_PROVIDER == "openai":
        return ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=os.getenv("OPENAI_API_KEY"),
            max_retries=4,
            **kwargs,
        )

    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        max_retries=4,
        **kwargs,
    )
