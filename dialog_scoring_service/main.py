from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import numpy as np
import uvicorn

app = FastAPI()
model = SentenceTransformer('intfloat/multilingual-e5-small')

class EvaluationRequest(BaseModel):
    vacancy_description: str
    hard_skills: list[str]
    soft_skills: list[str]
    candidate_answers: list[str]

class EvaluationResponse(BaseModel):
    score_dialog: float
    explanation: str = ""

@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(req: EvaluationRequest):

    job_text = req.vacancy_description + " " + " ".join(req.hard_skills + req.soft_skills)
    job_emb = model.encode(job_text)


    answer_embs = [model.encode(ans) for ans in req.candidate_answers if ans]
    if not answer_embs:
        return EvaluationResponse(score_dialog=0.0, explanation="Нет ответов")


    avg_answer_emb = np.mean(answer_embs, axis=0)


    similarity = np.dot(job_emb, avg_answer_emb)

    score = (similarity + 1) / 2
    score = float(np.clip(score, 0, 1))

    return EvaluationResponse(score_dialog=score, explanation="Семантическая близость к требованиям")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)