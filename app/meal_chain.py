from datetime import datetime, date
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from sqlalchemy.orm import Session

from app.ai_text import text_of
from app.database import SessionLocal
from app.llm import get_chat_model
from app.models import MealLog


def get_today_meal_summary(user_id: str) -> str:
    db: Session = SessionLocal()
    today = date.today()
    try:
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        meals = (
            db.query(MealLog)
            .filter(MealLog.user_id == user_id, MealLog.meal_time >= start, MealLog.meal_time <= end)
            .order_by(MealLog.meal_time).all()
        )
        if not meals:
            return "No meals logged for today."
        return "\n".join(f"[{meal.meal_time.strftime('%H:%M')}] {meal.summary}" for meal in meals)
    finally:
        db.close()


COACH_SYSTEM = (
    "You are FitSense, a friendly certified nutritionist who knows Indonesian cuisine well.\n"
    "Meals the user logged today:\n{meal_context}\n\n"
    "Answer the user's questions with practical health and nutrition guidance grounded in those meals. "
    "Always reply in English. Keep answers concise (under ~180 words unless asked for more). "
    "Format with light Markdown: short paragraphs, **bold** for key points, and bullet lists where useful. "
    "Do not use tables unless the user asks for one."
)


def get_coach_chain_with_meal_context(user_id: str) -> Runnable:
    meal_context = get_today_meal_summary(user_id)
    prompt = ChatPromptTemplate.from_messages([
        ("system", COACH_SYSTEM),
        MessagesPlaceholder(variable_name="history", optional=True),
        ("human", "{input}"),
    ])
    llm = get_chat_model(temperature=0.5)
    return prompt.partial(meal_context=meal_context) | llm


def generate_daily_insight(meal_context: str, totals: dict, targets: dict) -> Optional[str]:
    """Short narrative about today's intake. Returns None if the model is unavailable."""
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a certified Indonesian nutrition coach. The user's meals today:\n{meal_context}\n\n"
         "Estimated totals: {calories} kcal, {protein} g protein, {carbs} g carbohydrates, {fat} g fat.\n"
         "Reference daily targets: {t_calories} kcal, {t_protein} g protein, {t_carbs} g carbohydrates, {t_fat} g fat.\n\n"
         "In English, write 2-3 short sentences summarising today's intake, highlighting one strength and one concern, "
         "then one concrete improvement for the next meal. Use **bold** for the improvement. No headings, no lists."),
        ("human", "Summarise my day."),
    ])
    try:
        chain = prompt | get_chat_model(temperature=0.4)
        response = chain.invoke({
            "meal_context": meal_context,
            "calories": round(totals["calories"]), "protein": round(totals["protein"]),
            "carbs": round(totals["carbohydrates"]), "fat": round(totals["fat"]),
            "t_calories": targets["calories"], "t_protein": targets["protein"],
            "t_carbs": targets["carbohydrates"], "t_fat": targets["fat"],
        })
        return text_of(response) or None
    except Exception as exc:
        print(f"Daily insight generation failed: {exc}")
        return None
