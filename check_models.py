"""Check available Gemini models."""
import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyDdwslGU16sbYihnIuYQTz_siR7wiSlS64"))

print("Available Gemini models:")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"  - {model.name}")

