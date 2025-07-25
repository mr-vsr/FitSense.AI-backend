from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI

from models import SessionLocal, User, MealLog
import os

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

store = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

def get_user_meal_history(user_id: str) -> str:
    db = SessionLocal()
    user = db.query(User).filter(User.username == user_id).first()
    if not user:
        return "No meal history found."

    meals = (
        db.query(MealLog)
        .filter(MealLog.user_id == user.id)
        .order_by(MealLog.meal_time.desc())
        .limit(7)
        .all()
    )

    if not meals:
        return "No meal history found."

    return "\n".join([
        f"{meal.meal_time.date()}: {meal.summary}" for meal in meals
    ])

def get_meal_assistant_chain(user_id: str):
    meal_history_text = get_user_meal_history(user_id)

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a health coach AI. Use the following user's 7-day meal history to help answer questions:\n{meal_history_text}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])

    chain = prompt | llm
    return RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history"
    )
