import os
import json
from dotenv import load_dotenv
from PIL import Image
from google import generativeai as genai

# Load API key
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def detect_food_items(image_path: str) -> list[str]:
    # Load image as a PIL object
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
    "5. Based on your analysis, suggest 2–3 additional traditional Indonesian foods that are simple, commonly available at home (e.g., tempeh, boiled egg, sayur lodeh, tahu goreng, buah segar), "
    "which would improve the overall nutrition of the meal.\n\n"

    "Respond in this exact JSON format:\n"
    "{\n"
    "  \"food_items\": [\"item1\", \"item2\", ...],\n"
    "  \"nutrition\": {\n"
    "    \"item1\": {\n"
    "      \"calories\": 0,\n"
    "      \"fat\": 0.0,\n"
    "      \"protein\": 0.0,\n"
    "      \"carbohydrates\": 0.0\n"
    "    },\n"
    "    ...\n"
    "  },\n"
    "  \"summary\": \"<brief analysis of the meal's nutritional balance>\",\n"
    "  \"diet_suggestions\": [\"add this\", \"include that\"]\n"
    "}"
)




    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content([prompt, image])
    print("Gemini Raw Response:", response.text)

    try:
        result = json.loads(response.text)
        if isinstance(result, list):
            return [item.strip().lower() for item in result]
        return [str(result).strip().lower()]
    except json.JSONDecodeError:
        return [response.text.strip().lower()]