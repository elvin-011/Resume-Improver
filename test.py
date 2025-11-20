import google.generativeai as genai
import os

# Set your API key as an environment variable (recommended)
# or replace os.environ.get('GEMINI_API_KEY') with your key string
api_key = "AIzaSyAFJR0KmiccimEECP0OJX1NELYggjQ8m_A" 

try:
    genai.configure(api_key=api_key)
    # Attempt to list available models as a simple check
    models = [m.name for m in genai.list_models()]
    print("API key is working. Available models:", models)
except Exception as e:
    print(f"API key is not working. Error: {e}")
