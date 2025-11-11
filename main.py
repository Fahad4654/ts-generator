from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import date
import pandas as pd
import random
import re

# Load .env
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file")

genai.configure(api_key=api_key)

# Paths
OUTPUT_DIR = Path("src")
TOPICS_FILE = Path("topics.csv")

OUTPUT_DIR.mkdir(exist_ok=True)

def clean_code_block(code: str) -> str:
    """Remove markdown formatting like ```typescript ... ```"""
    code = re.sub(r"^```[a-zA-Z]*", "", code)
    code = re.sub(r"```$", "", code)
    return code.strip()


def get_unused_topic() -> str:
    """Fetch a random unused topic from topics.csv."""
    if not TOPICS_FILE.exists():
        raise FileNotFoundError("❌ topics.csv not found")

    df = pd.read_csv(TOPICS_FILE)

    unused = df[df["used"] == False]

    if unused.empty:
        raise ValueError("✅ All topics have been used!")

    topic = random.choice(unused["topic"].tolist())

    # Mark as used
    df.loc[df["topic"] == topic, "used"] = True
    df.to_csv(TOPICS_FILE, index=False)

    return topic


@app.get("/")
def home():
    return {"message": "🚀 Gemini Daily TypeScript Generator API running!"}


@app.get("/generate-daily")
def generate_daily_code():
    """Generate a unique TypeScript code file using an unused topic."""
    today = date.today().isoformat()

    try:
        topic = get_unused_topic()
    except Exception as e:
        return {"error": str(e)}

    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = f"""
    Generate a unique, self-contained TypeScript code snippet about: {topic}.
    Do not include explanations — only valid TypeScript code.
    """

    response = model.generate_content(prompt)
    code = clean_code_block(response.text.strip())

    safe_topic = re.sub(r"[^a-zA-Z0-9_-]", "_", topic)
    file_path = OUTPUT_DIR / f"{safe_topic}_code_sample_{today}.ts"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)

    return {
        "date": today,
        "topic": topic,
        "file": str(file_path),
        "code": code,
    }
