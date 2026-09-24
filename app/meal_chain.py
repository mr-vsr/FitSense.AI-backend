from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import MealLog
from app.llm import get_chat_model
from datetime import datetime, date
from sqlalchemy import Date

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

def get_coach_chain_with_meal_context(user_id: str) -> Runnable:
    meal_context = get_today_meal_summary(user_id)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a certified Indonesian nutritionist assistant. Based on the following meals consumed today:\n{meal_context}\nGive health and nutrition guidance or answer user questions. Keep the advice in english only"),
        ("human", "{input}")
    ])
    llm = get_chat_model(temperature=0.5)
    return prompt.partial(meal_context=meal_context) | llm

def generate_daily_summary(user_id: str) -> str:
    db: Session = SessionLocal()
    today = date.today()
    try:
        meals = (
            db.query(MealLog)
            .filter(MealLog.user_id == user_id, MealLog.meal_time.cast(Date) == today)
            .order_by(MealLog.meal_time).all()
        )
        if not meals:
            return "No meals logged today."
        meal_context = "\n".join(f"[{meal.meal_time.strftime('%H:%M')}] {meal.summary}" for meal in meals)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You're a certified Indonesian nutrition coach. Based on the user's meals today:\n{meal_context}\nSummarize the user's dietary intake in 2–3 sentences, highlight any nutritional strengths or concerns, and suggest one improvement in English.\nReturn ONLY a JSON object in this exact format:\n{{\n    \"totalCalories\": 14530,\n    \"avgCalories\": 2071,\n    \"protein\": 420,\n    \"carbs\": 1800,\n    \"fat\": 580,\n    \"meals\": 21,\n    \"goals\": {{\n        \"calories\": 85,\n        \"protein\": 92,\n        \"carbs\": 50,\n        \"fat\": 88\n    }}\n}}\nAvoid extra commentary. The output must be valid JSON."),
            ("human", "Please generate the daily summary.")
        ])
        llm = get_chat_model(temperature=0.5)
        chain = prompt.partial(meal_context=meal_context) | llm
        response = chain.invoke({"input": ""})
        return response.content if hasattr(response, "content") else response
    finally:
        db.close()
