#!/usr/bin/env python3
"""
MedAI LLM Integration Test Script
Test all LLM models to see which ones are working
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("🤖 MedAI LLM Integration Test")
print("=" * 60)
print()

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def test_claude():
    """Test Claude API"""
    print(f"{YELLOW}Testing Claude API...{RESET}")
    
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print(f"{RED}✗ Claude API key not found in .env{RESET}")
        return False
    
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Simple test
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": "Patient has fever and cough. What could it be? Reply in one sentence."
            }]
        )
        
        response_text = message.content[0].text
        print(f"{GREEN}✓ Claude API is working!{RESET}")
        print(f"  Sample response: {response_text[:80]}...")
        return True
        
    except ImportError:
        print(f"{RED}✗ anthropic library not installed. Run: pip install anthropic{RESET}")
        return False
    except Exception as e:
        print(f"{RED}✗ Claude API error: {str(e)}{RESET}")
        if "API key" in str(e):
            print(f"  Please check your CLAUDE_API_KEY in .env")
        return False

def test_openai():
    """Test OpenAI API"""
    print(f"{YELLOW}Testing OpenAI API...{RESET}")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print(f"{RED}✗ OpenAI API key not found in .env{RESET}")
        return False
    
    try:
        import openai
        
        openai.api_key = api_key
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": "Patient has fever and cough. What could it be? Reply in one sentence."
            }],
            max_tokens=100
        )
        
        response_text = response['choices'][0]['message']['content']
        print(f"{GREEN}✓ OpenAI API is working!{RESET}")
        print(f"  Sample response: {response_text[:80]}...")
        return True
        
    except ImportError:
        print(f"{RED}✗ openai library not installed. Run: pip install openai{RESET}")
        return False
    except Exception as e:
        print(f"{RED}✗ OpenAI API error: {str(e)}{RESET}")
        if "invalid_api_key" in str(e):
            print(f"  Please check your OPENAI_API_KEY in .env")
        if "billing" in str(e):
            print(f"  Please add payment method to OpenAI account")
        return False

def test_huggingface():
    """Test Hugging Face API"""
    print(f"{YELLOW}Testing Hugging Face API...{RESET}")

    api_key = os.getenv('HUGGINGFACE_API_KEY')

    # Debug line
    print(f"Token found: {bool(api_key)}")

    if not api_key:
        print(f"{RED}✗ Hugging Face API key not found in .env{RESET}")
        return False

    try:
        import requests

        # API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
        API_URL = "https://router.huggingface.co/hf-inference/models/google/gemma-2-2b-it"
        # API_URL = "https://router.huggingface.co/hf-inference/models/mistralai/Mistral-7B-Instruct-v0.1"
        headers = {"Authorization": f"Bearer {api_key}"}

        response = requests.post(
            API_URL,
            headers=headers,
            json={"inputs": "Patient has fever and cough. What could it be?"},
            timeout=30
        )

        if response.status_code == 200:
            print(f"{GREEN}✓ Hugging Face API is working!{RESET}")
            return True
        else:
            print(f"{RED}✗ Hugging Face API error: {response.status_code}{RESET}")
            print(f"  {response.text[:100]}")
            return False

    except Exception as e:
        print(f"{RED}✗ Hugging Face API error: {str(e)}{RESET}")
        return False

def test_mongodb():
    """Test MongoDB connection"""
    print(f"{YELLOW}Testing MongoDB...{RESET}")
    
    try:
        from pymongo import MongoClient
        
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/medai_db')
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Try to get server info
        client.admin.command('ping')
        
        print(f"{GREEN}✓ MongoDB is connected!{RESET}")
        print(f"  Connected to: {mongo_uri}")
        return True
        
    except ImportError:
        print(f"{RED}✗ pymongo library not installed. Run: pip install pymongo{RESET}")
        return False
    except Exception as e:
        print(f"{RED}✗ MongoDB connection error: {str(e)}{RESET}")
        print(f"  Make sure MongoDB is running: mongod")
        return False

def main():
    """Run all tests"""
    
    print("🔍 Checking environment configuration...")
    print()
    
    # Check .env file
    if os.path.exists('.env'):
        print(f"{GREEN}✓ .env file found{RESET}")
    else:
        print(f"{YELLOW}⚠ .env file not found (will use environment variables){RESET}")
    
    print()
    print("🧪 Running API Tests...")
    print()
    
    results = {}
    
    # Test each API
    results['Claude'] = test_claude()
    print()
    
    results['OpenAI'] = test_openai()
    print()
    
    results['Hugging Face'] = test_huggingface()
    print()
    
    results['MongoDB'] = test_mongodb()
    print()
    
    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    working_llms = [name for name, status in results.items() if status and name != 'MongoDB']
    mongodb_ok = results.get('MongoDB', False)
    
    if working_llms:
        print(f"{GREEN}✓ Working LLMs: {', '.join(working_llms)}{RESET}")
    else:
        print(f"{YELLOW}⚠ No LLMs configured. Will use rule-based fallback.{RESET}")
    
    if mongodb_ok:
        print(f"{GREEN}✓ MongoDB is ready{RESET}")
    else:
        print(f"{RED}✗ MongoDB needs to be running{RESET}")
    
    print()
    
    # Recommendations
    print("💡 Recommendations:")
    print()
    
    if not working_llms and not mongodb_ok:
        print("1. Start MongoDB: mongod")
        print("2. Add API keys to .env file")
        print("3. Run: pip install -r requirements_with_llm.txt")
    elif not working_llms:
        print("1. Add API keys to .env file")
        print("2. Choose one of: Claude, OpenAI, or Hugging Face")
        print("3. Run: pip install -r requirements_with_llm.txt")
    elif not mongodb_ok:
        print("1. Install MongoDB: https://www.mongodb.com/try/download/community")
        print("2. Start MongoDB: mongod")
        print("3. Run: pip install pymongo")
    else:
        print(f"{GREEN}✓ Everything is ready! Run: python app_with_llm.py{RESET}")
    
    print()
    print("=" * 60)
    
    return 0 if (mongodb_ok and working_llms) else 1

if __name__ == '__main__':
    sys.exit(main())