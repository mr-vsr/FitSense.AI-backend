import json
import os
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime


from app.gemini_utils import detect_food_items
from app.models import User, MealLog, NutritionalData
from app.database import SessionLocal
from app.meal_chain import get_coach_chain_with_meal_context, generate_daily_summary
from app.health_tip import generate_health_tip

router = APIRouter()
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class UserMessage(BaseModel):
    user_id: str
    message: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/upload")
async def upload_image(
    image: UploadFile = File(...),
    user_id: str = Form(...),
    height: float = Form(None),
    weight: float = Form(None)
):
    db: Session = next(get_db())

    try:
        image_path = os.path.join(UPLOAD_FOLDER, f"{user_id}_{datetime.now().isoformat()}_{image.filename}")
        with open(image_path, "wb") as buffer:
            buffer.write(await image.read())

        # Detect food items using Gemini
        food_items = detect_food_items(image_path)

        # Simulated nutrition values — replace with actual logic if needed
        nutrition_data = {
            "calories": 400.0,
            "protein": 15.0,
            "fat": 10.0,
            "carbohydrates": 55.0
        }

        # Create or update user
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(user_id=user_id, username=user_id, height_cm=height, weight_kg=weight)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Save meal log
        meal = MealLog(
            user_id=user.user_id,
            image_path=image_path,
            summary=f"Detected: {', '.join(food_items)}",
            meal_time=datetime.now()
        )
        db.add(meal)
        db.commit()
        db.refresh(meal)

        # Save nutrition
        nutrition = NutritionalData(
            meal_id=meal.id,
            **nutrition_data
        )
        db.add(nutrition)
        db.commit()

        return {
            "message": "Meal uploaded and processed",
            "detected_food_items": food_items,
            "meal_id": meal.id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat-meal-coach/")
async def chat_meal_coach(
    user_id:str=Form(...),
    message:str=Form(...)
):
    # print(payload)
    try:
        # ✅ Validate user
        db: Session = SessionLocal()
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ✅ Let the chain fetch today's meals internally
        coach_chain = get_coach_chain_with_meal_context(user.user_id)

        # ✅ Send user message to the LLM
        response = coach_chain.invoke({"input": message})

        # ✅ Return response content
        return {
            "reply": response.content if hasattr(response, "content") else response
        }
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        meals = (
            db.query(MealLog)
            .filter(MealLog.user_id == user.user_id)
            .filter(MealLog.meal_time >= today_start)
            .filter(MealLog.meal_time <= today_end)
            .order_by(MealLog.meal_time.asc())
            .all()
        )
        if not meals:
            meal_context = "The user hasn't logged any meals today."
        else:
            meal_context = "\n".join([
                f"{meal.meal_time.strftime('%H:%M')}: {meal.summary}" for meal in meals
            ])
        coach_chain = get_coach_chain_with_meal_context(meal_context)
        response = coach_chain.invoke({"input": message})
        return {"reply": response.content}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


# @router.get("/generate-daily-report/{user_id}")
# async def generate_weekly_report(user_id: str):
#     try:
#         daily_report = generate_daily_summary(user_id)
#         # print(daily_report)
#         cleaned = daily_report.replace('\\n', '').replace('json', '').replace('```', '').strip()
#         # print(cleaned)
#         try:
#             parsed = json.loads(daily_report)
#             # print(parsed)
#         except json.JSONDecodeError as e:
#             print("❌ JSON parse error:", e)
#         if parsed:
#             meals_per_day = parsed.get("meals", 2)
#             total_meals = 21
#             factor = total_meals / meals_per_day
#             weeklyData = {
#             "totalCalories": round(parsed["totalCalories"] * factor),
#             "avgCalories": round((parsed["totalCalories"] * factor) / total_meals),
#             "protein": round(parsed["protein"] * factor),
#             "carbs": round(parsed["carbs"] * factor),
#             "fat": round(parsed["fat"] * factor),
#             "meals": total_meals,
#             "goals": parsed.get("goals", {})  # Use provided goals
#             }
#             print("✅ weeklyData:", weeklyData)
#         else:
#             print("❌ No valid data to process.")
#         return {daily_report}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@router.get("/generate-daily-report/{user_id}")
async def generate_weekly_report(user_id: str):
    try:
        daily_report = generate_daily_summary(user_id)

        # Step 1: Clean the string (remove \n, ``` and `json` prefix)
        cleaned = daily_report.replace('\\n', '').replace('json', '').replace('```', '').strip()

        # Step 2: Parse JSON
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            print("❌ JSON parse error:", e)
            raise HTTPException(status_code=400, detail="Invalid JSON format in daily_report.")

        # Step 3: Generate weekly summary
        meals_per_day = parsed.get("meals", 2)
        total_meals = 21
        factor = total_meals / meals_per_day

        weekly_data = {
            "totalCalories": round(parsed["totalCalories"] * factor),
            "avgCalories": round((parsed["totalCalories"] * factor) / total_meals),
            "protein": round(parsed["protein"] * factor),
            "carbs": round(parsed["carbs"] * factor),
            "fat": round(parsed["fat"] * factor),
            "meals": total_meals,
            "goals": parsed.get("goals", {})
        }

        # Optional debug
        print("✅ weeklyData:", weekly_data)

        # Step 4: Return JSON response
        return {"weekly_summary": weekly_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-tip/{user_id}")
async def get_daily_health_tip(user_id: str):
    try:
        tip = generate_health_tip(user_id)
        return {"daily_tip": tip}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
