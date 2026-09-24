import os
import time
import base64
import mimetypes
from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types
from openai import OpenAI

from app.ai_text import extract_json, to_number

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-5.6-luna")

gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY")) if os.getenv("GOOGLE_API_KEY") else None
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

MACROS = ("calories", "protein", "carbohydrates", "fat")

MEAL_PROMPT = (
    "You are a certified nutritionist and dietician specialised in Indonesian cuisine "
    "who follows the Indonesian Ministry of Health dietary guidelines (Pedoman Gizi Seimbang).\n\n"
    "Look at the photo and:\n"
    "1. Identify every visible food or drink item, estimating a realistic single-serving portion.\n"
    "2. Estimate calories (kcal) and protein, carbohydrates and fat (grams) for each item.\n"
    "3. Write a 2-3 sentence summary of the meal's nutritional balance: what is sufficient, "
    "what is lacking or excessive, and whether it is balanced per the guidelines.\n"
    "4. Suggest 2-3 simple, commonly available Indonesian foods (e.g. tempeh, boiled egg, "
    "sayur lodeh, tahu, fresh fruit) that would improve the meal. Keep each suggestion to one short sentence.\n\n"
    "Rules: respond in English with ONLY valid JSON, no markdown fences, no commentary. "
    "Numbers must be plain numbers without units. Keys in \"nutrition\" must exactly match the names in \"food_items\". "
    "If there is no food in the photo, return an empty food_items list.\n\n"
    "JSON format:\n"
    "{\n"
    "  \"food_items\": [\"Nasi putih\", \"Ayam goreng\"],\n"
    "  \"nutrition\": {\n"
    "    \"Nasi putih\": {\"calories\": 204, \"protein\": 4.2, \"carbohydrates\": 44.5, \"fat\": 0.4}\n"
    "  },\n"
    "  \"summary\": \"...\",\n"
    "  \"diet_suggestions\": [\"...\", \"...\"]\n"
    "}"
)


def _is_transient_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(term in message for term in (
        "429", "500", "502", "503", "504",
        "unavailable", "high demand", "service unavailable",
        "rate limit", "timeout",
    ))


def _with_retries(label: str, fn):
    for attempt in range(4):
        try:
            return fn()
        except Exception as exc:
            if not _is_transient_error(exc) or attempt == 3:
                raise
            delay = 2 ** attempt
            print(f"{label} temporarily unavailable; retrying in {delay}s (attempt {attempt + 1}/4)")
            time.sleep(delay)


def _generate_with_gemini(prompt: str, image_path: str) -> str:
    if gemini_client is None:
        raise RuntimeError("GOOGLE_API_KEY is not configured.")
    with Image.open(image_path) as img:
        image = img.convert("RGB")

    def call():
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return response.text

    return _with_retries("Gemini", call)


def _generate_with_openai(prompt: str, image_path: str) -> str:
    if openai_client is None:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    with open(image_path, "rb") as image_file:
        image_b64 = base64.b64encode(image_file.read()).decode("utf-8")

    def call():
        response = openai_client.responses.create(
            model=OPENAI_VISION_MODEL,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:{mime};base64,{image_b64}"},
                ],
            }],
        )
        return response.output_text

    return _with_retries("OpenAI", call)


def _normalize(raw) -> dict:
    """Turn whatever the model returned into a predictable shape for the API/UI."""
    if isinstance(raw, list):
        raw = {"food_items": raw}
    if not isinstance(raw, dict):
        raise ValueError("Unexpected analysis format from the model.")

    nutrition_raw = raw.get("nutrition") or {}
    if isinstance(nutrition_raw, list):  # [{"name": "...", "calories": ...}]
        nutrition_raw = {
            str(entry.get("name") or entry.get("item") or f"Item {i + 1}"): entry
            for i, entry in enumerate(nutrition_raw) if isinstance(entry, dict)
        }

    nutrition = {}
    for name, values in nutrition_raw.items():
        if not isinstance(values, dict):
            continue
        values = {str(k).lower(): v for k, v in values.items()}
        if "carbohydrates" not in values and "carbs" in values:
            values["carbohydrates"] = values["carbs"]
        nutrition[str(name).strip()] = {m: round(to_number(values.get(m)), 1) for m in MACROS}

    food_items = [str(i).strip() for i in (raw.get("food_items") or []) if str(i).strip()]
    if not food_items:
        food_items = list(nutrition)

    totals = {m: round(sum(item[m] for item in nutrition.values()), 1) for m in MACROS}

    suggestions = raw.get("diet_suggestions") or []
    if isinstance(suggestions, str):
        suggestions = [suggestions]

    return {
        "food_items": food_items,
        "nutrition": nutrition,
        "totals": totals,
        "summary": str(raw.get("summary") or "").strip(),
        "diet_suggestions": [str(s).strip() for s in suggestions if str(s).strip()],
    }


def analyze_meal(image_path: str) -> dict:
    """Run the vision model on a meal photo and return structured nutrition data."""
    providers = ["gemini", "openai"] if LLM_PROVIDER != "openai" else ["openai", "gemini"]
    errors = []

    for provider in providers:
        try:
            if provider == "gemini":
                response_text = _generate_with_gemini(MEAL_PROMPT, image_path)
            else:
                response_text = _generate_with_openai(MEAL_PROMPT, image_path)
            analysis = _normalize(extract_json(response_text))
            print(f"{provider} meal analysis succeeded.")
            return analysis
        except Exception as exc:
            errors.append(f"{provider}: {exc}")
            print(f"{provider} meal analysis failed: {exc}")

    raise RuntimeError("All configured AI providers failed. " + " | ".join(errors))


def detect_food_items(image_path: str) -> list:
    """Backwards-compatible helper: only the detected item names."""
    return [item.lower() for item in analyze_meal(image_path)["food_items"]]
