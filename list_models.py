#this class has nothing with the project, just to see available models from gemini.


import os
import google.generativeai as genai
from dotenv import load_dotenv, find_dotenv

# .env yükle (backend klasöründe çalıştırdığından emin ol)

load_dotenv(find_dotenv(), override=True)

API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise SystemExit("❌ No API key found. Set GOOGLE_API_KEY in your .env")

genai.configure(api_key=API_KEY)

available = []
for m in genai.list_models():
    if "generateContent" in getattr(m, "supported_generation_methods", []):
        available.append(m.name)

print("✅ Available (generateContent):")
for name in available:
    print("-", name)

    #çıktı : models/gemini-2.5-flash bunu kullanacağım