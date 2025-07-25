from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import MealLog
from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
import os


def generate_health_tip(user_id: str, days: int = 3) -> str:
    db: Session = SessionLocal()
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        meals = (
            db.query(MealLog)
            .filter(
                MealLog.user_id == user_id,
                MealLog.meal_time >= start_time,
                MealLog.meal_time <= end_time
            )
            .order_by(MealLog.meal_time)
            .all()
        )

        if not meals:
            return "No recent meals found. Please log your meals to receive a health tip."

        # Concatenate summaries
        meal_summary = "\n".join([
            f"[{meal.meal_time.strftime('%Y-%m-%d %H:%M')}] {meal.summary}" for meal in meals
        ])

        # Prepare prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a certified Indonesian nutritionist assistant. "
             "Based on the following meal history:\n"
             "{meal_summary}\n"
             "Give a single, short health tip (1 sentence) to help improve the user's nutrition. Keep the tip in english"),
            ("human", "What’s a useful health tip for me?")
        ])

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.5,
        )

        chain = prompt.partial(meal_summary=meal_summary) | llm
        response = chain.invoke({"input": "Generate a daily health tip"})

        return response.content if hasattr(response, 'content') else response

    except Exception as e:
        return f"Error generating health tip: {str(e)}"

    finally:
        db.close()
