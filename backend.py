import os
import json
import uuid
import zipfile
import asyncio
from dotenv import load_dotenv  # Добавьте этот импорт

from fastapi import FastAPI, UploadFile
from pdfminer.high_level import extract_text
from docx import Document
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from groq import Groq
from telegram import Bot

# Загружаем переменные из .env файла
load_dotenv()

# ------------------------
# CONFIG
# ------------------------

# Получаем значения из переменных окружения
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверяем, что ключи загружены
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY не найден в переменных окружения")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

# Инициализируем клиенты
client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=BOT_TOKEN)

app = FastAPI()

# ------------------------
# MEMORY STORAGE
# ------------------------

vacancy = {}

candidates = {}

# ------------------------
# PARSERS
# ------------------------

def parse_pdf(path):
    return extract_text(path)

def parse_docx(path):
    doc = Document(path)
    return "\n".join([p.text for p in doc.paragraphs])

def parse_resume(path):

    if path.endswith(".pdf"):
        return parse_pdf(path)

    if path.endswith(".docx"):
        return parse_docx(path)

    return ""

# ------------------------
# LLM EXTRACTION
# ------------------------

def extract_candidate(resume_text):

    prompt = f"""
You are an expert HR resume parser.

Extract detailed structured information from the resume.

Resume:
{resume_text}

Return STRICT JSON:

name
email
phone
location
telegram_username

total_years_experience
current_position
seniority_level

skills_technical
skills_soft

programming_languages
frameworks
databases
cloud
tools

education
languages

previous_companies
projects

english_level

key_strengths
possible_weaknesses

salary_expectation

summary

Return ONLY JSON.
"""

    response = client.chat.completions.create(
        model="llama-3.1-70b",
        messages=[{"role":"user","content":prompt}],
        temperature=0
    )

    text = response.choices[0].message.content

    return json.loads(text)

# ------------------------
# MATCHING
# ------------------------

def score_candidate(candidate):

    prompt = f"""
You are an HR AI that evaluates candidate fit for a vacancy.

VACANCY:

title: {vacancy['title']}
required_skills: {vacancy['skills']}
description: {vacancy['description']}
seniority: {vacancy['seniority']}

CANDIDATE:

{candidate}

Evaluate candidate fit.

Consider:

skills match
experience
seniority
relevant technologies
english
career stability

Return STRICT JSON:

score (0-100)
match_strengths
match_gaps
reason
"""

    response = client.chat.completions.create(
        model="llama-3.1-70b",
        messages=[{"role":"user","content":prompt}],
        temperature=0
    )

    text = response.choices[0].message.content

    return json.loads(text)

# ------------------------
# TELEGRAM
# ------------------------

async def send_message(username):

    try:

        message = """
Hello!

Your resume matched our vacancy.

We would like to ask you a few quick screening questions.

Please reply to start the interview.
"""

        await bot.send_message(
            chat_id=f"@{username}",
            text=message
        )

    except Exception as e:
        print("telegram error:", e)

# ------------------------
# API
# ------------------------

@app.post("/create_vacancy")
async def create_vacancy(data: dict):

    vacancy["title"] = data["title"]
    vacancy["skills"] = data["skills"]
    vacancy["description"] = data["description"]
    vacancy["seniority"] = data["seniority"]

    return {"status":"vacancy_created"}

# ------------------------

@app.post("/upload_resumes")
async def upload_resumes(file: UploadFile):

    with open("resumes.zip","wb") as f:
        f.write(await file.read())

    with zipfile.ZipFile("resumes.zip",'r') as zip_ref:
        zip_ref.extractall("resumes")

    for filename in os.listdir("resumes"):

        path = f"resumes/{filename}"

        text = parse_resume(path)

        candidate = extract_candidate(text)

        match = score_candidate(candidate)

        cid = str(uuid.uuid4())

        candidates[cid] = {
            "data": candidate,
            "score": match["score"],
            "analysis": match
        }

    return {"parsed": len(candidates)}

# ------------------------

@app.post("/start_screening")
async def start_screening(data: dict):

    n = data["n"]

    sorted_candidates = sorted(
        candidates.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    top_candidates = sorted_candidates[:n]

    sent = []

    for cid, cand in top_candidates:

        username = cand["data"].get("telegram_username")

        if username:

            await send_message(username)

            sent.append(username)

    return {
        "contacted_candidates": sent
    }

# ------------------------

@app.get("/candidates")
def get_candidates():

    sorted_candidates = sorted(
        candidates.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    return sorted_candidates