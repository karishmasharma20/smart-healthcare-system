import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://router.huggingface.co/hf-inference/models/google/flan-t5-base"

headers = {
    "Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}"
}

def analyze_symptoms(symptoms):
    prompt = f"Analyze these symptoms and suggest possible conditions: {symptoms}"

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json={"inputs": prompt},
            timeout=30
        )

        return {
            "status_code": response.status_code,
            "response": response.text
        }

    except Exception as e:
        return {
            "error": str(e)
        }