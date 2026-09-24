from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from langchain_core.prompts import ChatPromptTemplate

from app.ai_text import text_of
from app.database import SessionLocal
from app.llm import get_chat_model
from app.models import MealLog


def generate_health_tip(user_id: str, days: int = 3) -> str:
    db: Session = SessionLocal()
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        meals = (
            db.query(MealLog)
            .filter(MealLog.user_id == user_id, MealLog.meal_time >= start_time, MealLog.meal_time <= end_time)
            .order_by(MealLog.meal_time).all()
        )
    finally:
        db.close()

    if not meals:
        return "No recent meals found. Analyze a meal first to receive a personalised health tip."

    meal_summary = "\n".join(f"[{meal.meal_time.strftime('%Y-%m-%d %H:%M')}] {meal.summary}" for meal in meals)
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a certified Indonesian nutritionist assistant. The user's recent meals:\n{meal_summary}\n\n"
         "Give ONE short, specific, actionable health tip (a single sentence, max 30 words) that would most improve "
         "their nutrition. English only. Plain text: no quotes, no markdown, no preamble."),
        ("human", "What's a useful health tip for me today?"),
    ])
    try:
        chain = prompt.partial(meal_summary=meal_summary) | get_chat_model(temperature=0.6)
        tip = text_of(chain.invoke({})).strip().strip('"')
        return tip or "Drink a glass of water before each meal and add one serving of vegetables to your next plate."
    except Exception as exc:
        print(f"Health tip generation failed: {exc}")
        return "We couldn't reach the AI right now. Try again in a moment."
