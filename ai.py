import requests
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def extract_content_name_ai(text: str) -> str:
    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gemini-2.0-flash",  # lightweight, fast model
        "messages": [
            {"role": "system", "content": "You are an expert in Entertainment and OTT sector that extracts only the content name (title only without year along with season-episode count if mentioned like S01, S03E05, etc) from input text."},
            {"role": "user", "content": text} 
        ],
        "temperature": 0
    }

    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()

# Example usage
#input_text = """Star.Trek.Strange.New.Worlds.S03E07.What.Is.Starfleet.2160p.JSTAR.WEB-DL.AAC2.0.H.265-4kHdHub.Com.mkv"""
#print(extract_content_name_ai(input_text))
