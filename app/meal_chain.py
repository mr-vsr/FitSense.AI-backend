from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import MealLog
from datetime import datetime, date
from sqlalchemy import Date
import os

# 🔍 Fetch today's meal summary for a user
def get_today_meal_summary(user_id: str) -> str:
    db: Session = SessionLocal()
    today = date.today()

    try:
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())

        meals = (
            db.query(MealLog)
            .filter(
                MealLog.user_id == user_id,
                MealLog.meal_time >= start,
                MealLog.meal_time <= end
            )
            .order_by(MealLog.meal_time)
            .all()
        )

        if not meals:
            return "No meals logged for today."

        summaries = [
            f"[{meal.meal_time.strftime('%H:%M')}] {meal.summary}" for meal in meals
        ]
        return "\n".join(summaries)

    finally:
        db.close()


# 🧠 Creates the coach chain with meal context
def get_coach_chain_with_meal_context(user_id: str) -> Runnable:
    meal_context = get_today_meal_summary(user_id)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a certified Indonesian nutritionist assistant. Based on the following meals consumed today:\n"
            "{meal_context}\n"
            "Give health and nutrition guidance or answer user questions. Keep the advice in english only"
        ),
        ("human", "{input}")
    ])

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.5,
    )

    return prompt.partial(meal_context=meal_context) | llm

def generate_daily_summary(user_id: str) -> str:
    db: Session = SessionLocal()
    today = date.today()

    try:
        # ✅ Get today's meals from summary column
        meals = (
            db.query(MealLog)
            .filter(
                MealLog.user_id == user_id,
                MealLog.meal_time.cast(Date) == today
            )
            .order_by(MealLog.meal_time)
            .all()
        )

        if not meals:
            return "No meals logged today."

        # 📋 Format meal summary text
        summary_lines = [
            f"[{meal.meal_time.strftime('%H:%M')}] {meal.summary}" for meal in meals
        ]
        meal_context = "\n".join(summary_lines)

        # 🧠 Prompt for Gemini
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You're a certified Indonesian nutrition coach. Based on the user's meals today:\n"
                "{meal_context}\n"
                "Summarize the user's dietary intake in 2–3 sentences, highlight any nutritional strengths or concerns, and suggest one improvement in English."
            ),
            ("human", "Please generate the daily summary.")
        ])

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.5,
        )

        chain = prompt.partial(meal_context=meal_context) | llm
        response = chain.invoke({"input": ""})

        return response.content if hasattr(response, "content") else response

    finally:
        db.close()