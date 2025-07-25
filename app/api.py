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
async def chat_meal_coach(payload: UserMessage):
    db: Session = SessionLocal()

    try:
        # ✅ Validate user
        user = db.query(User).filter(User.user_id == payload.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ✅ Let the chain fetch today's meals internally
        coach_chain = get_coach_chain_with_meal_context(user.user_id)

        # ✅ Send user message to the LLM
        response = coach_chain.invoke({"input": payload.message})

        # ✅ Return response content
        return {
            "reply": response.content if hasattr(response, "content") else response
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@router.get("/generate-daily-report/{user_id}")
async def generate_weekly_report(user_id: str):
    try:
        daily_report = generate_daily_summary(user_id)
        return {"daily_report": daily_report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-tip/{user_id}")
async def get_daily_health_tip(user_id: str):
    try:
        tip = generate_health_tip(user_id)
        return {"daily_tip": tip}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
