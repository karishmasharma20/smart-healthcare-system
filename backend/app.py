from fastapi import FastAPI, Depends, HTTPException, status, Header, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId
import jwt
import hashlib
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import requests
from dotenv import load_dotenv
import anthropic
import json

load_dotenv()

app = FastAPI(title="MedAI Backend", version="1.0.0")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
JWT_EXPIRATION_SECONDS = 7 * 24 * 60 * 60  # 7 days

# Database connection initialization
client = AsyncIOMotorClient(MONGO_URI)
db = client['medai_db']

# API Keys
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY', '')

# ============ PYDANTIC SCHEMAS (Validation) ============

class SignupModel(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = ""

class LoginModel(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdateModel(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None

# ============ HELPER FUNCTIONS & MIDDLEWARE ============

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token is missing")
    
    try:
        token_type, token = authorization.split(" ")
        if token_type.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        
        # Check if user exists
        user = await db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        return user_id
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid ObjectId structure")

# ============ AI ANALYSIS WITH LLM ============

def analyze_with_claude(symptoms: str):
    if not CLAUDE_API_KEY:
        return None
    try:
        client_anthropic = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        prompt = f"""You are a medical diagnostic AI assistant. Based on the following symptoms, provide... [same prompt as before]"""
        
        message = client_anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text
        
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(response_text[json_start:json_end])
    except Exception as e:
        print(f"Claude API Error: {str(e)}")
    return None

def analyze_with_openai(symptoms: str):
    if not OPENAI_API_KEY:
        return None
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        prompt = f"""You are a medical diagnostic AI. Analyze these symptoms: {symptoms}..."""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        response_text = response['choices'][0]['message']['content']
        
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(response_text[json_start:json_end])
    except Exception as e:
        print(f"OpenAI API Error: {str(e)}")
    return None

def analyze_with_huggingface(symptoms: str):
    if not HUGGINGFACE_API_KEY:
        return None
    try:
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
        prompt = f"Analyze these medical symptoms and provide diagnosis:\nSymptoms: {symptoms}\n\nProvide top 3 conditions with confidence scores as JSON."
        
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Hugging Face API Error: {str(e)}")
    return None

def analyze_with_fallback(symptoms: str):
    disease_db = {
        'Common Cold': {
            'keywords': ['cough', 'runny nose', 'sore throat', 'sneezing'],
            'description': 'A viral infection affecting the upper respiratory tract',
            'recommendations': ['Get rest', 'Drink fluids', 'Use saline drops', 'Gargle salt water'],
            'severity': 'mild'
        },
        'Flu (Influenza)': {
            'keywords': ['fever', 'body ache', 'chills', 'cough', 'fatigue'],
            'description': 'A contagious respiratory illness caused by influenza virus',
            'recommendations': ['Stay home', 'Rest', 'Monitor temperature', 'Drink fluids'],
            'severity': 'moderate'
        }
    }
    symptoms_lower = symptoms.lower()
    diagnosis = []
    
    for disease, info in disease_db.items():
        matched = sum(1 for keyword in info['keywords'] if keyword in symptoms_lower)
        if matched > 0:
            confidence = min((matched / len(info['keywords'])) * 100, 100)
            diagnosis.append({
                'name': disease,
                'description': info['description'],
                'confidence': int(confidence),
                'recommendations': info['recommendations'],
                'severity': info['severity']
            })
    
    diagnosis.sort(key=lambda x: x['confidence'], reverse=True)
    return {
        'diagnosis': diagnosis[:3],
        'urgent_warning': None,
        'general_notes': 'Using rule-based analysis. For accurate diagnosis, consult a healthcare professional.'
    }

# ============ AUTHENTICATION ROUTES ============

@app.post('/api/auth/signup', status_code=201)
async def signup(data: SignupModel):
    existing_user = await db.users.find_one({'email': data.email})
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    user = {
        'name': data.name,
        'email': data.email,
        'password': hash_password(data.password),
        'phone': data.phone,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    result = await db.users.insert_one(user)
    user_id = str(result.inserted_id)
    
    token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION_SECONDS)
    }, SECRET_KEY, algorithm='HS256')
    
    return {
        'message': 'User created successfully',
        'token': token,
        'user': {'id': user_id, 'name': data.name, 'email': data.email}
    }

@app.post('/api/auth/login')
async def login(data: LoginModel):
    user = await db.users.find_one({'email': data.email})
    if not user or user['password'] != hash_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = jwt.encode({
        'user_id': str(user['_id']),
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION_SECONDS)
    }, SECRET_KEY, algorithm='HS256')
    
    return {
        'message': 'Login successful',
        'token': token,
        'user': {'id': str(user['_id']), 'name': user['name'], 'email': user['email']}
    }

# ============ ANALYSIS ROUTES ============

@app.post('/api/analysis/analyze')
async def analyze_symptoms(
    symptoms: str = Form(...),
    file: Optional[UploadFile] = File(None),
    user_id: str = Depends(get_current_user_id)
):
    symptoms = symptoms.strip()
    if not symptoms:
        raise HTTPException(status_code=400, detail="No symptoms provided")
    
    diagnosis_result = None
    analysis_method = 'rule-based'
    
    if CLAUDE_API_KEY:
        diagnosis_result = analyze_with_claude(symptoms)
        if diagnosis_result: analysis_method = 'Claude AI'
        
    if not diagnosis_result and OPENAI_API_KEY:
        diagnosis_result = analyze_with_openai(symptoms)
        if diagnosis_result: analysis_method = 'OpenAI GPT'
        
    if not diagnosis_result and HUGGINGFACE_API_KEY:
        diagnosis_result = analyze_with_huggingface(symptoms)
        if diagnosis_result: analysis_method = 'Hugging Face'
        
    if not diagnosis_result:
        diagnosis_result = analyze_with_fallback(symptoms)
        analysis_method = 'Rule-based (Fallback)'
        
    analysis_record = {
        'user_id': ObjectId(user_id),
        'symptoms': symptoms,
        'diagnosis': diagnosis_result.get('diagnosis', []),
        'analysis_method': analysis_method,
        'timestamp': datetime.now(),
        'file_uploaded': file is not None
    }
    
    result = await db.analyses.insert_one(analysis_record)
    
    return {
        'message': f'Analysis completed using {analysis_method}',
        'analysis_id': str(result.inserted_id),
        'diagnosis': diagnosis_result.get('diagnosis', []),
        'analysis_method': analysis_method,
        'urgent_warning': diagnosis_result.get('urgent_warning'),
        'general_notes': diagnosis_result.get('general_notes')
    }

@app.get('/api/analysis/history')
async def get_analysis_history(user_id: str = Depends(get_current_user_id)):
    cursor = db.analyses.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1).limit(50)
    analyses = await cursor.to_list(length=50)
    
    for analysis in analyses:
        analysis['_id'] = str(analysis['_id'])
        analysis['user_id'] = str(analysis['user_id'])
        analysis['timestamp'] = analysis['timestamp'].isoformat()
        
    return {'message': 'History retrieved', 'analyses': analyses}

@app.delete('/api/analysis/{analysis_id}')
async def delete_analysis(analysis_id: str, user_id: str = Depends(get_current_user_id)):
    await db.analyses.delete_one({'_id': ObjectId(analysis_id), 'user_id': ObjectId(user_id)})
    return {'message': 'Analysis deleted'}

# ============ USER ROUTES ============

@app.get('/api/user/profile')
async def get_user_profile(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({'_id': ObjectId(user_id)})
    return {
        'user': {
            'id': str(user['_id']),
            'name': user['name'],
            'email': user['email'],
            'phone': user.get('phone', ''),
            'created_at': user['created_at'].isoformat()
        }
    }

@app.put('/api/user/profile')
async def update_user_profile(data: ProfileUpdateModel, user_id: str = Depends(get_current_user_id)):
    update_data: Dict[str, Any] = {}
    if data.name is not None: update_data['name'] = data.name
    if data.phone is not None: update_data['phone'] = data.phone
    
    update_data['updated_at'] = datetime.now()
    
    await db.users.update_one({'_id': ObjectId(user_id)}, {'$set': update_data})
    return {'message': 'Profile updated successfully'}

# ============ SYSTEM STATUS ============

@app.get('/api/system/status')
def system_status():
    llm_available = []
    if CLAUDE_API_KEY: llm_available.append('Claude AI')
    if OPENAI_API_KEY: llm_available.append('OpenAI GPT')
    if HUGGINGFACE_API_KEY: llm_available.append('Hugging Face')
        
    return {
        'status': 'running',
        'message': 'MedAI Backend is active',
        'llm_models': llm_available if llm_available else ['Rule-based (Fallback)'],
        'timestamp': datetime.now().isoformat()
    }

@app.get('/api/health')
def health_check():
    return {
        'status': 'running',
        'message': 'MedAI Backend is active',
        'timestamp': datetime.now().isoformat()
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host='localhost', port=5000, reload=True)