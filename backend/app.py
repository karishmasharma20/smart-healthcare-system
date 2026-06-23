from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import jwt
import hashlib
import os
from datetime import datetime, timedelta
from functools import wraps
import requests
from dotenv import load_dotenv
import anthropic
import json

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost:27017/medai_db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
app.config['JWT_EXPIRATION'] = 7 * 24 * 60 * 60  # 7 days

mongo = PyMongo(app)

# ============ LLM CONFIGURATION ============

# Option 1: Using Claude (Anthropic)
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')

# Option 2: Using OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Option 3: Using Hugging Face
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY', '')

# ============ MIDDLEWARE ============

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if not user:
                return jsonify({'message': 'User not found'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(user_id, *args, **kwargs)
    
    return decorated

# ============ AUTHENTICATION ROUTES ============

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    
    if not all(key in data for key in ['name', 'email', 'password']):
        return jsonify({'message': 'Missing required fields'}), 400
    
    if mongo.db.users.find_one({'email': data['email']}):
        return jsonify({'message': 'Email already registered'}), 409
    
    user = {
        'name': data['name'],
        'email': data['email'],
        'password': hash_password(data['password']),
        'phone': data.get('phone', ''),
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    result = mongo.db.users.insert_one(user)
    user_id = result.inserted_id
    
    token = jwt.encode({
        'user_id': str(user_id),
        'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_EXPIRATION'])
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'message': 'User created successfully',
        'token': token,
        'user': {
            'id': str(user_id),
            'name': data['name'],
            'email': data['email']
        }
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing email or password'}), 400
    
    user = mongo.db.users.find_one({'email': data['email']})
    
    if not user or user['password'] != hash_password(data['password']):
        return jsonify({'message': 'Invalid email or password'}), 401
    
    token = jwt.encode({
        'user_id': str(user['_id']),
        'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_EXPIRATION'])
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'id': str(user['_id']),
            'name': user['name'],
            'email': user['email']
        }
    }), 200

# ============ AI ANALYSIS WITH LLM ============

def analyze_with_claude(symptoms):
    """
    Uses Claude AI (Anthropic) for medical diagnosis
    """
    if not CLAUDE_API_KEY:
        return None
    
    try:
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        
        prompt = f"""You are a medical diagnostic AI assistant. Based on the following symptoms, provide:
1. Top 3-5 most likely conditions (with confidence percentage)
2. Detailed description of each condition
3. Recommended actions/treatments
4. When to seek immediate medical attention

Symptoms: {symptoms}

Format your response as JSON with this structure:
{{
    "diagnosis": [
        {{
            "name": "Condition Name",
            "confidence": 85,
            "description": "Brief description",
            "recommendations": ["action1", "action2"],
            "severity": "mild|moderate|severe"
        }}
    ],
    "urgent_warning": "If applicable, emergency warning",
    "general_notes": "Additional notes"
}}

IMPORTANT: This is for educational purposes. Always recommend consulting a healthcare professional."""
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text
        
        # Try to parse JSON from response
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                diagnosis = json.loads(json_str)
                return diagnosis
        except:
            pass
        
        return None
    except Exception as e:
        print(f"Claude API Error: {str(e)}")
        return None

def analyze_with_openai(symptoms):
    """
    Uses OpenAI GPT for medical diagnosis
    """
    if not OPENAI_API_KEY:
        return None
    
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        
        prompt = f"""You are a medical diagnostic AI. Analyze these symptoms: {symptoms}

Provide 3-5 possible conditions with:
- Name
- Confidence (0-100%)
- Description
- Recommendations
- Severity level

Format as JSON."""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        response_text = response['choices'][0]['message']['content']
        
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                diagnosis = json.loads(json_str)
                return diagnosis
        except:
            pass
        
        return None
    except Exception as e:
        print(f"OpenAI API Error: {str(e)}")
        return None

def analyze_with_huggingface(symptoms):
    """
    Uses Hugging Face models for medical diagnosis
    """
    if not HUGGINGFACE_API_KEY:
        return None
    
    try:
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
        
        prompt = f"""Analyze these medical symptoms and provide diagnosis:
Symptoms: {symptoms}

Provide top 3 conditions with confidence scores as JSON."""
        
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        
        if response.status_code == 200:
            result = response.json()
            return result
        
        return None
    except Exception as e:
        print(f"Hugging Face API Error: {str(e)}")
        return None

def analyze_with_fallback(symptoms):
    """
    Fallback: Simple rule-based diagnosis if LLM fails
    """
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
        },
        'Migraine': {
            'keywords': ['headache', 'throbbing', 'nausea', 'light sensitivity'],
            'description': 'Severe headache often accompanied by other symptoms',
            'recommendations': ['Rest in dark room', 'Apply cold compress', 'Stay hydrated'],
            'severity': 'moderate'
        },
        'Allergies': {
            'keywords': ['itching', 'sneezing', 'runny nose', 'watery eyes', 'rash'],
            'description': 'Immune system reaction to allergens',
            'recommendations': ['Avoid allergen', 'Use antihistamines', 'Clean environment'],
            'severity': 'mild'
        },
        'Gastroenteritis': {
            'keywords': ['nausea', 'vomiting', 'stomach pain', 'diarrhea'],
            'description': 'Infection of the digestive system',
            'recommendations': ['Stay hydrated', 'Eat bland foods', 'Rest', 'Seek medical help if severe'],
            'severity': 'moderate'
        },
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
        'diagnosis': diagnosis[:3] if diagnosis else [],
        'urgent_warning': None,
        'general_notes': 'Using rule-based analysis. For accurate diagnosis, consult a healthcare professional.'
    }

# ============ ANALYSIS ROUTES ============

@app.route('/api/analysis/analyze', methods=['POST'])
@token_required
def analyze_symptoms(user_id):
    symptoms = request.form.get('symptoms', '').strip()
    
    if not symptoms:
        return jsonify({'message': 'No symptoms provided'}), 400
    
    # Try LLM models in order
    diagnosis_result = None
    analysis_method = 'rule-based'
    
    # Try Claude first
    if CLAUDE_API_KEY:
        diagnosis_result = analyze_with_claude(symptoms)
        if diagnosis_result:
            analysis_method = 'Claude AI'
    
    # Try OpenAI if Claude fails
    if not diagnosis_result and OPENAI_API_KEY:
        diagnosis_result = analyze_with_openai(symptoms)
        if diagnosis_result:
            analysis_method = 'OpenAI GPT'
    
    # Try Hugging Face if others fail
    if not diagnosis_result and HUGGINGFACE_API_KEY:
        diagnosis_result = analyze_with_huggingface(symptoms)
        if diagnosis_result:
            analysis_method = 'Hugging Face'
    
    # Use fallback if all LLMs fail
    if not diagnosis_result:
        diagnosis_result = analyze_with_fallback(symptoms)
        analysis_method = 'Rule-based (Fallback)'
    
    # Save to database
    analysis_record = {
        'user_id': ObjectId(user_id),
        'symptoms': symptoms,
        'diagnosis': diagnosis_result.get('diagnosis', []),
        'analysis_method': analysis_method,
        'timestamp': datetime.now(),
        'file_uploaded': 'file' in request.files
    }
    
    result = mongo.db.analyses.insert_one(analysis_record)
    
    return jsonify({
        'message': f'Analysis completed using {analysis_method}',
        'analysis_id': str(result.inserted_id),
        'diagnosis': diagnosis_result.get('diagnosis', []),
        'analysis_method': analysis_method,
        'urgent_warning': diagnosis_result.get('urgent_warning'),
        'general_notes': diagnosis_result.get('general_notes')
    }), 200

@app.route('/api/analysis/history', methods=['GET'])
@token_required
def get_analysis_history(user_id):
    analyses = list(mongo.db.analyses.find(
        {'user_id': ObjectId(user_id)}
    ).sort('timestamp', -1).limit(50))
    
    for analysis in analyses:
        analysis['_id'] = str(analysis['_id'])
        analysis['user_id'] = str(analysis['user_id'])
        analysis['timestamp'] = analysis['timestamp'].isoformat()
    
    return jsonify({
        'message': 'History retrieved',
        'analyses': analyses
    }), 200

@app.route('/api/analysis/<analysis_id>', methods=['DELETE'])
@token_required
def delete_analysis(user_id, analysis_id):
    mongo.db.analyses.delete_one({
        '_id': ObjectId(analysis_id),
        'user_id': ObjectId(user_id)
    })
    
    return jsonify({'message': 'Analysis deleted'}), 200

# ============ USER ROUTES ============

@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_user_profile(user_id):
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    
    return jsonify({
        'user': {
            'id': str(user['_id']),
            'name': user['name'],
            'email': user['email'],
            'phone': user.get('phone', ''),
            'created_at': user['created_at'].isoformat()
        }
    }), 200

@app.route('/api/user/profile', methods=['PUT'])
@token_required
def update_user_profile(user_id):
    data = request.json
    
    update_data = {}
    if 'name' in data:
        update_data['name'] = data['name']
    if 'phone' in data:
        update_data['phone'] = data['phone']
    
    update_data['updated_at'] = datetime.now()
    
    mongo.db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': update_data}
    )
    
    return jsonify({'message': 'Profile updated successfully'}), 200

# ============ SYSTEM STATUS ============

@app.route('/api/system/status', methods=['GET'])
def system_status():
    llm_available = []
    
    if CLAUDE_API_KEY:
        llm_available.append('Claude AI')
    if OPENAI_API_KEY:
        llm_available.append('OpenAI GPT')
    if HUGGINGFACE_API_KEY:
        llm_available.append('Hugging Face')
    
    return jsonify({
        'status': 'running',
        'message': 'MedAI Backend is active',
        'llm_models': llm_available if llm_available else ['Rule-based (Fallback)'],
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'running',
        'message': 'MedAI Backend is active',
        'timestamp': datetime.now().isoformat()
    }), 200

# ============ ERROR HANDLERS ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)