# Food Insight API
#This API allows users to upload a food image, detects items in it, provides nutritional info, and suggests diet adjustments.

## Run locally:
```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Example curl:
```
curl -X POST "http://localhost:8000/upload/" -F "file=@sample.jpg"
```

## Add a .env file:
```
GEMINI_API_KEY=your_google_generative_ai_key
```