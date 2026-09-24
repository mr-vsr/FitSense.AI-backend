import json
import os
import re
import uuid
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.concurrency import run_in_threadpool
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.exc import SQLAlchemyError

from app.ai_text import text_of
from app.database import SessionLocal
from app.gemini_utils import analyze_meal
from app.health_tip import generate_health_tip
from app.meal_chain import get_coach_chain_with_meal_context, generate_daily_insight
from app.models import User, MealLog, NutritionalData

router = APIRouter()
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_HISTORY_TURNS = 12

DB_UNAVAILABLE = "Your meal data is temporarily unavailable. Please try again in a moment."
USER_NOT_FOUND = "We couldn't find this user. Analyze a meal first using this User ID."


def _clean_user_id(user_id: str) -> str:
    user_id = (user_id or "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="Please enter a User ID.")
    if len(user_id) > 64:
        raise HTTPException(status_code=400, detail="User ID must be 64 characters or fewer.")
    return user_id


def _safe_filename_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)[:40]


def _fmt(n: float) -> str:
    return f"{n:.0f}" if n >= 10 else f"{n:.1f}"


def _meal_summary(analysis: dict) -> str:
    """Compact text stored with the meal; this is what the coach and tips read later."""
    t = analysis["totals"]
    line = (
        f"{', '.join(analysis['food_items'])} — ~{_fmt(t['calories'])} kcal, "
        f"protein {_fmt(t['protein'])} g, carbs {_fmt(t['carbohydrates'])} g, fat {_fmt(t['fat'])} g."
    )
    if analysis.get("summary"):
        line += f" Note: {analysis['summary']}"
    return line


def _targets(user: User) -> dict:
    """Generic reference daily values (2,000 kcal diet); protein scales with weight when known."""
    protein = round(user.weight_kg * 0.8) if user.weight_kg else 50
    return {"calories": 2000, "protein": max(protein, 40), "carbohydrates": 275, "fat": 78}


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user_id = _clean_user_id(user_id)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
        meal_count = db.query(MealLog).filter(MealLog.user_id == user_id).count()
        return {
            "user_id": user.user_id,
            "height_cm": user.height_cm,
            "weight_kg": user.weight_kg,
            "meal_count": meal_count,
        }
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE)
    finally:
        db.close()


@router.post("/upload")
async def upload_image(
    image: UploadFile = File(...),
    user_id: str = Form(...),
    height: Optional[float] = Form(None),
    weight: Optional[float] = Form(None),
):
    user_id = _clean_user_id(user_id)

    extension = os.path.splitext(image.filename or "")[1].lower() or ".jpg"
    if extension not in ALLOWED_EXTENSIONS or (image.content_type and not image.content_type.startswith("image/")):
        raise HTTPException(status_code=400, detail="Please upload a JPG, PNG or WEBP photo of your meal.")

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="That photo is larger than 10 MB. Please upload a smaller one.")

    image_path = os.path.join(
        UPLOAD_FOLDER,
        f"{_safe_filename_part(user_id)}_{datetime.now():%Y%m%d-%H%M%S}_{uuid.uuid4().hex[:8]}{extension}",
    )
    with open(image_path, "wb") as buffer:
        buffer.write(data)

    try:
        analysis = await run_in_threadpool(analyze_meal, image_path)
    except Exception as exc:
        print(f"Meal analysis failed: {exc}")
        raise HTTPException(status_code=502, detail="We couldn't analyze this photo right now. Please try again in a moment.")

    if not analysis["food_items"]:
        raise HTTPException(status_code=422, detail="We couldn't spot any food in this photo. Try a clearer, well-lit shot of your plate.")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(user_id=user_id, username=user_id, height_cm=height, weight_kg=weight)
            db.add(user)
        else:
            if height:
                user.height_cm = height
            if weight:
                user.weight_kg = weight

        meal = MealLog(
            user_id=user_id,
            image_path=image_path,
            summary=_meal_summary(analysis),
            meal_time=datetime.now(),
        )
        db.add(meal)
        db.flush()

        totals = analysis["totals"]
        db.add(NutritionalData(
            meal_id=meal.id,
            calories=totals["calories"],
            protein=totals["protein"],
            fat=totals["fat"],
            carbohydrates=totals["carbohydrates"],
        ))
        db.commit()

        return {
            "message": "Meal uploaded and processed",
            "meal_id": meal.id,
            "detected_food_items": analysis["food_items"],
            **analysis,
        }
    except SQLAlchemyError as exc:
        db.rollback()
        print(f"Saving meal failed: {exc}")
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE)
    finally:
        db.close()


def _parse_history(raw: Optional[str]) -> list:
    if not raw:
        return []
    try:
        turns = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(turns, list):
        return []

    messages = []
    for turn in turns[-MAX_HISTORY_TURNS:]:
        if not isinstance(turn, dict) or not isinstance(turn.get("content"), str):
            continue
        content = turn["content"][:4000]
        if turn.get("role") == "user":
            messages.append(HumanMessage(content=content))
        elif turn.get("role") == "assistant":
            messages.append(AIMessage(content=content))
    return messages


@router.post("/chat-meal-coach/")
async def chat_meal_coach(
    user_id: str = Form(...),
    message: str = Form(...),
    history: Optional[str] = Form(None),
):
    user_id = _clean_user_id(user_id)
    message = (message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Please type a question for your coach.")

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.user_id == user_id).first():
            raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE)
    finally:
        db.close()

    try:
        coach_chain = get_coach_chain_with_meal_context(user_id)
        response = await run_in_threadpool(
            coach_chain.invoke, {"input": message, "history": _parse_history(history)}
        )
        reply = text_of(response)
        if not reply:
            raise ValueError("Empty reply from model")
        return {"reply": reply}
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE)
    except Exception as exc:
        print(f"Coach chat failed: {exc}")
        raise HTTPException(status_code=500, detail="Sorry, the coach couldn't respond right now. Please try again.")


@router.get("/generate-daily-report/{user_id}")
async def generate_daily_report(user_id: str):
    """Today's nutrition totals from logged meals, a 7-day calorie trend and an AI insight."""
    user_id = _clean_user_id(user_id)
    today = date.today()
    week_start = datetime.combine(today - timedelta(days=6), datetime.min.time())
    day_end = datetime.combine(today, datetime.max.time())

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

        rows = (
            db.query(MealLog, NutritionalData)
            .outerjoin(NutritionalData, NutritionalData.meal_id == MealLog.id)
            .filter(MealLog.user_id == user_id, MealLog.meal_time >= week_start, MealLog.meal_time <= day_end)
            .order_by(MealLog.meal_time.asc())
            .all()
        )
        targets = _targets(user)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE)
    finally:
        db.close()

    week = {}
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        week[d] = {"date": d.isoformat(), "label": d.strftime("%a"), "calories": 0.0, "meals": 0}

    totals = {"calories": 0.0, "protein": 0.0, "carbohydrates": 0.0, "fat": 0.0}
    meals = []
    for meal, nutrition in rows:
        day = meal.meal_time.date()
        kcal = (nutrition.calories or 0.0) if nutrition else 0.0
        if day in week:
            week[day]["calories"] += kcal
            week[day]["meals"] += 1
        if day == today:
            if nutrition:
                totals["calories"] += nutrition.calories or 0.0
                totals["protein"] += nutrition.protein or 0.0
                totals["carbohydrates"] += nutrition.carbohydrates or 0.0
                totals["fat"] += nutrition.fat or 0.0
            meals.append({
                "id": meal.id,
                "time": meal.meal_time.strftime("%H:%M"),
                "items": (meal.summary or "").split(" — ")[0].replace("Detected: ", ""),
                "calories": round(kcal),
            })

    if not meals:
        raise HTTPException(status_code=404, detail="No meals logged today yet. Analyze a meal to see your report.")

    totals = {k: round(v, 1) for k, v in totals.items()}
    goals = {k: round(totals[k] / targets[k] * 100) if targets[k] else 0 for k in totals}
    meal_context = "\n".join(f"[{m['time']}] {m['items']} (~{m['calories']} kcal)" for m in meals)
    insight = await run_in_threadpool(generate_daily_insight, meal_context, totals, targets)

    for entry in week.values():
        entry["calories"] = round(entry["calories"])

    return {
        "date": today.isoformat(),
        "totals": totals,
        "targets": targets,
        "goals": goals,
        "meals": meals,
        "week": list(week.values()),
        "insight": insight,
    }


@router.get("/daily-tip/{user_id}")
async def get_daily_health_tip(user_id: str):
    user_id = _clean_user_id(user_id)
    try:
        tip = await run_in_threadpool(generate_health_tip, user_id)
        return {"daily_tip": tip}
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE)
    except Exception:
        raise HTTPException(status_code=500, detail="Sorry, we couldn't generate a health tip right now. Please try again.")
