import os
import json
import time
import base64
from dotenv import load_dotenv
from PIL import Image
from google import genai
from openai import OpenAI

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-5.6-luna")

gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None


def _is_transient_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(term in message for term in (
        "429", "500", "502", "503", "504",
        "unavailable", "high demand", "service unavailable",
        "rate limit", "timeout",
    ))


def _generate_with_gemini(prompt: str, image: Image.Image) -> str:
    last_error = None
    for attempt in range(4):
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[prompt, image],
            )
            return response.text
        except Exception as exc:
            last_error = exc
            if not _is_transient_error(exc) or attempt == 3:
                raise
            delay = 2 ** attempt
            print(f"Gemini temporarily unavailable; retrying in {delay}s (attempt {attempt + 1}/4)")
            time.sleep(delay)
    raise last_error


def _generate_with_openai(prompt: str, image_path: str) -> str:
    if openai_client is None:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    with open(image_path, "rb") as image_file:
        image_b64 = base64.b64encode(image_file.read()).decode("utf-8")

    last_error = None
    for attempt in range(4):
        try:
            response = openai_client.responses.create(
                model=OPENAI_VISION_MODEL,
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image_b64}",
                        },
                    ],
                }],
            )
            return response.output_text
        except Exception as exc:
            last_error = exc
            if not _is_transient_error(exc) or attempt == 3:
                raise
            delay = 2 ** attempt
            print(f"OpenAI temporarily unavailable; retrying in {delay}s (attempt {attempt + 1}/4)")
            time.sleep(delay)
    raise last_error


def detect_food_items(image_path: str) -> list[str]:
    image = Image.open(image_path)

    prompt = (
        "You are a certified nutritionist and dietician specialized in Indonesian cuisine "
        "and follow the official dietary guidelines by the Indonesian Ministry of Health "
        "(Pedoman Gizi Seimbang).\n\n"
        "Tasks:\n"
        "1. Identify all visible food items in the given image.\n"
        "2. Return only a clean JSON list of food item names (no explanations).\n"
        "3. Provide nutritional values for each identified item using trusted sources "
        "(calories, fat, protein, carbohydrates).\n"
        "4. Analyze the total nutritional value of the meal, and give a brief health summary stating:\n"
        "   - What nutrients are sufficient\n"
        "   - What nutrients are lacking or excessive\n"
        "   - Whether the meal is balanced according to Indonesian dietary guidelines\n\n"
        "5. Based on your analysis, suggest 2–3 additional traditional Indonesian foods "
        "that are simple, commonly available at home (e.g., tempeh, boiled egg, sayur lodeh, "
        "tahu goreng, buah segar), which would improve the overall nutrition of the meal.\n\n"
        "Respond in this exact JSON format:\n"
        "{\n"
        "  \"food_items\": [\"item1\", \"item2\", ...],\n"
        "  \"nutrition\": {\n"
        "    \"item1\": {\"calories\": 0, \"fat\": 0.0, "
        "\"protein\": 0.0, \"carbohydrates\": 0.0}\n"
        "  },\n"
        "  \"summary\": \"<brief analysis of the meal's nutritional balance>\",\n"
        "  \"diet_suggestions\": [\"add this\", \"include that\"]\n"
        "}"
    )

    providers = ["gemini", "openai"] if LLM_PROVIDER != "openai" else ["openai", "gemini"]
    errors = []

    for provider in providers:
        try:
            if provider == "gemini":
                response_text = _generate_with_gemini(prompt, image)
            else:
                response_text = _generate_with_openai(prompt, image_path)
            print(f"{provider} response received successfully.")
            break
        except Exception as exc:
            errors.append(f"{provider}: {exc}")
            print(f"{provider} generation failed: {exc}")
    else:
        raise RuntimeError("All configured AI providers failed. " + " | ".join(errors))

    try:
        result = json.loads(response_text)
        if isinstance(result, dict) and isinstance(result.get("food_items"), list):
            return [str(item).strip().lower() for item in result["food_items"]]
        if isinstance(result, list):
            return [str(item).strip().lower() for item in result]
        return [str(result).strip().lower()]
    except json.JSONDecodeError:
        return [response_text.strip().lower()]
