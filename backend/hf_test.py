
import socket




try:
    print("IP:", socket.gethostbyname("api-inference.huggingface.co"))
except Exception as e:
    print("DNS Error:", e)

from dotenv import load_dotenv
import os
import requests

load_dotenv()

import joblib

le = joblib.load("../models/label_encoder.pkl")

candidate_labels = list(le.classes_)


api_key = os.getenv("HUGGINGFACE_API_KEY")

url = "https://api-inference.huggingface.co/models/google/flan-t5-base"

headers = {
    "Authorization": f"Bearer {api_key}"
}

payload = {
    "inputs": "Patient has fever and cough",
    "parameters": {
        "candidate_labels": candidate_labels
    }
}
response = requests.post(
    url,
    headers=headers,
    json=payload
)

print("Status:", response.status_code)
print("Response:", response.text)