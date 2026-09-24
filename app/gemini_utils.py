import os
import json
import time
from dotenv import load_dotenv
from PIL import Image
from google import genai

# Load API key
load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def detect_food_items(image_path: str) -> list[str]:
    image = Image.open(image_path)

    prompt = (
    "You are a certified nutritionist and dietician specialized in Indonesian cuisine and follow the official dietary guidelines by the Indonesian Ministry of Health (Pedoman Gizi Seimbang).\n\n"
    "Tasks:\n"
    "1. Identify all visible food items in the given image.\n"
    "2. Return only a clean JSON list of food item names (no explanations).\n"
    "3. Provide nutritional values for each identified item using trusted sources (calories, fat, protein, carbohydrates).\n"
    "4. Analyze the total nutritional value of the meal, and give a brief health summary stating:\n"
    "   - What nutrients are sufficient\n"
    "   - What nutrients are lacking or excessive\n"
    "   - Whether the meal is balanced according to Indonesian dietary guidelines\n\n"
    "5. Based on your analysis, suggest 2–3 additional traditional Indonesian foods that are simple, commonly available at home (e.g., tempeh, boiled egg, sayur lodeh, tahu goreng, buah segar), which would improve the overall nutrition of the meal.\n\n"
    "Respond in this exact JSON format:\n"
    "{\n"
    "  \"food_items\": [\"item1\", \"item2\", ...],\n"
    "  \"nutrition\": {\n"
    "    \"item1\": {\"calories\": 0, \"fat\": 0.0, \"protein\": 0.0, \"carbohydrates\": 0.0}\n"
    "  },\n"
    "  \"summary\": \"<brief analysis of the meal's nutritional balance>\",\n"
    "  \"diet_suggestions\": [\"add this\", \"include that\"]\n"
    "}"
    )

    last_error = None
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[prompt, image],
            )
            break
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            transient = any(term in message for term in (
                "503", "unavailable", "high demand", "service unavailable"
            ))
            if not transient or attempt == 3:
                raise
            delay = 2 ** attempt
            print(f"Gemini temporarily unavailable; retrying in {delay}s (attempt {attempt + 1}/4)")
            time.sleep(delay)
    else:
        raise last_error

    print("Gemini Raw Response:", response.text)

    try:
        result = json.loads(response.text)
        if isinstance(result, dict) and isinstance(result.get("food_items"), list):
            return [str(item).strip().lower() for item in result["food_items"]]
        if isinstance(result, list):
            return [str(item).strip().lower() for item in result]
        return [str(result).strip().lower()]
    except json.JSONDecodeError:
        return [response.text.strip().lower()]