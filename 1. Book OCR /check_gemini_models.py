import google.generativeai as genai
import os

# Paste your API Key here directly for the test
API_KEY = "[ENCRYPTION_KEY]" 

genai.configure(api_key=API_KEY)

print("Checking available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")