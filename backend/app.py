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

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost:27017/medai_db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
app.config['JWT_EXPIRATION'] = 7 * 24 * 60 * 60  # 7 days

mongo = PyMongo(app)

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
    
    # Validation
    if not all(key in data for key in ['name', 'email', 'password']):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if user exists
    if mongo.db.users.find_one({'email': data['email']}):
        return jsonify({'message': 'Email already registered'}), 409
    
    # Create user
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
    
    # Generate token
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
    
    # Generate token
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

# ============ ANALYSIS ROUTES ============

@app.route('/api/analysis/analyze', methods=['POST'])
@token_required
def analyze_symptoms(user_id):
    symptoms = request.form.get('symptoms', '')
    
    if not symptoms:
        return jsonify({'message': 'No symptoms provided'}), 400
    
    # AI Analysis Logic
    diagnosis = perform_ai_analysis(symptoms)
    
    # Save to database
    analysis_record = {
        'user_id': ObjectId(user_id),
        'symptoms': symptoms,
        'diagnosis': diagnosis,
        'timestamp': datetime.now(),
        'file_uploaded': 'file' in request.files
    }
    
    result = mongo.db.analyses.insert_one(analysis_record)
    
    return jsonify({
        'message': 'Analysis completed',
        'analysis_id': str(result.inserted_id),
        'diagnosis': diagnosis
    }), 200

@app.route('/api/analysis/history', methods=['GET'])
@token_required
def get_analysis_history(user_id):
    analyses = list(mongo.db.analyses.find(
        {'user_id': ObjectId(user_id)}
    ).sort('timestamp', -1).limit(50))
    
    # Convert ObjectId to string for JSON serialization
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

# ============ AI ANALYSIS FUNCTION ============

def perform_ai_analysis(symptoms):
    """
    Performs AI-based symptom analysis.
    This is a basic implementation - integrate with actual ML model
    """
    
    # Disease database with symptoms mapping
    disease_db = {
        'Common Cold': {
            'keywords': ['cough', 'runny nose', 'sore throat', 'sneezing'],
            'description': 'A viral infection affecting the upper respiratory tract',
            'recommendations': [
                'Get adequate rest (7-9 hours)',
                'Drink plenty of fluids (water, herbal tea)',
                'Use saline nasal drops for congestion',
                'Gargle with salt water for sore throat',
                'Consider over-the-counter pain relievers'
            ]
        },
        'Flu (Influenza)': {
            'keywords': ['fever', 'body ache', 'chills', 'cough', 'fatigue'],
            'description': 'A contagious respiratory illness caused by influenza virus',
            'recommendations': [
                'Stay home and avoid contact with others',
                'Rest and drink plenty of fluids',
                'Monitor temperature regularly',
                'Use fever reducers if needed',
                'Seek medical attention if symptoms worsen'
            ]
        },
        'Allergies': {
            'keywords': ['itching', 'sneezing', 'runny nose', 'watery eyes', 'rash'],
            'description': 'Immune system reaction to allergens',
            'recommendations': [
                'Identify and avoid allergen sources',
                'Use antihistamines as needed',
                'Maintain a clean, dust-free environment',
                'Take warm showers to relieve congestion',
                'Consider allergy testing'
            ]
        },
        'Migraine': {
            'keywords': ['headache', 'throbbing', 'nausea', 'light sensitivity', 'vomiting'],
            'description': 'Severe headache often accompanied by other symptoms',
            'recommendations': [
                'Rest in a dark, quiet room',
                'Apply cold compress to forehead',
                'Stay hydrated',
                'Avoid caffeine and processed foods',
                'Consider prescription medication if severe'
            ]
        },
        'Gastrointestinal Infection': {
            'keywords': ['nausea', 'vomiting', 'stomach pain', 'diarrhea', 'loss of appetite'],
            'description': 'Infection of the digestive system',
            'recommendations': [
                'Stay hydrated with electrolyte solutions',
                'Eat bland, easy-to-digest foods',
                'Avoid dairy and fatty foods',
                'Rest as much as possible',
                'Seek medical attention if symptoms persist'
            ]
        },
        'Skin Infection': {
            'keywords': ['rash', 'itching', 'redness', 'swelling', 'pain'],
            'description': 'Bacterial or fungal skin infection',
            'recommendations': [
                'Keep the affected area clean and dry',
                'Apply antiseptic creams',
                'Avoid scratching to prevent spreading',
                'Wear loose, breathable clothing',
                'See a dermatologist if severe or spreading'
            ]
        }
    }
    
    symptoms_lower = symptoms.lower()
    diagnosis = []
    
    # Calculate probability for each disease
    for disease, info in disease_db.items():
        matched_keywords = sum(1 for keyword in info['keywords'] if keyword in symptoms_lower)
        
        if matched_keywords > 0:
            probability = min(matched_keywords / len(info['keywords']), 1.0)
            
            diagnosis.append({
                'name': disease,
                'description': info['description'],
                'confidence': probability,
                'recommendations': info['recommendations']
            })
    
    # Sort by confidence
    diagnosis.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Return top 3 diagnoses
    return diagnosis[:3]

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

# ============ HEALTH CHECK ============

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