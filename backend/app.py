from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import joblib
from pydantic import BaseModel
import pandas as pd
import json
from dotenv import load_dotenv
from google import genai
load_dotenv()
import fitz
from fastapi import UploadFile, File
client = genai.Client(
    api_key="AQ.Ab8RN6Js2xm9jZN8mzDPiuzzzzzzzzzzzzzzzzzzzzzz"
)

app = FastAPI(title="Smart Healthcare AI")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rf = joblib.load("../models/disease_model.pkl")
le = joblib.load("../models/label_encoder.pkl")

with open("../data/disease_info.json", "r") as f:
    disease_info = json.load(f)

all_symptoms = list(rf.feature_names_in_)


class SymptomsInput(BaseModel):
    symptoms: list[str]


class TextInput(BaseModel):
    text: str


def extract_symptoms(text):
    text = text.lower()

    found = []

    for symptom in all_symptoms:
        if symptom.replace("_", " ") in text:
            found.append(symptom)

    return found


@app.get("/")
def home():
    return {"message": "Smart Healthcare AI running"}


@app.post("/predict")
def predict(data: SymptomsInput):

    input_data = pd.DataFrame(
        0,
        index=[0],
        columns=rf.feature_names_in_
    )

    for symptom in data.symptoms:
        if symptom in input_data.columns:
            input_data[symptom] = 1

    prediction = rf.predict(input_data)

    probability = rf.predict_proba(input_data)

    confidence = round(
        max(probability[0]) * 100,
        2
    )

    disease = le.inverse_transform(prediction)

    disease_name = disease[0]

    info = disease_info.get(
        disease_name,
        {
            "description": "Information not available",
            "precautions": []
        }
    )

    return {
    "predicted_disease": disease_name,
    "confidence": confidence,
    "description": info["description"],
    "severity": info.get("severity", "Unknown"),
    "doctor_type": info.get("doctor_type", "General Physician"),
    "precautions": info["precautions"]
}


@app.post("/predict-text")
def predict_text(data: TextInput):

    symptoms = extract_symptoms(data.text)

    if len(symptoms) == 0:
        return {
            "message": "No symptoms detected"
        }

    input_data = pd.DataFrame(
        0,
        index=[0],
        columns=rf.feature_names_in_
    )

    for symptom in symptoms:
        input_data[symptom] = 1

    prediction = rf.predict(input_data)

    probability = rf.predict_proba(input_data)

    confidence = round(
        max(probability[0]) * 100,
        2
    )

    disease = le.inverse_transform(prediction)

    disease_name = disease[0]

    info = disease_info.get(
        disease_name,
        {
            "description": "Information not available",
            "severity": "Unknown",
            "doctor_type": "General Physician",
            "precautions": []
        }
    )

    return {
        "detected_symptoms": symptoms,
        "predicted_disease": disease_name,
        "confidence": confidence,
        "description": info["description"],
        "severity": info["severity"],
        "doctor_type": info["doctor_type"],
        "precautions": info["precautions"]
    }
@app.post("/analyze-pdf")
async def analyze_pdf(file: UploadFile = File(...)):

    pdf_bytes = await file.read()

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    text = ""

    for page in doc:
        text += page.get_text()

    return {
        "extracted_text": text[:3000]
    }