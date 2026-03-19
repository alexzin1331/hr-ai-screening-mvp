from __future__ import annotations

from functools import lru_cache

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None


MODEL_NAME = "intfloat/multilingual-e5-small"
app = FastAPI(title="Dialog Scoring Service")


class EvaluationRequest(BaseModel):
    vacancy_description: str
    hard_skills: list[str]
    soft_skills: list[str]
    candidate_answers: list[str]


class EvaluationResponse(BaseModel):
    score_dialog: float
    explanation: str = ""


@lru_cache
def get_model():
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers is not installed")
    return SentenceTransformer(MODEL_NAME)


@app.get("/health")
def health() -> dict[str, str]:
    try:
        get_model()
        return {"status": "ok", "model": MODEL_NAME}
    except Exception as exc:
        return {"status": "degraded", "model": MODEL_NAME, "error": str(exc)}


@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(req: EvaluationRequest) -> EvaluationResponse:
    answers = [answer.strip() for answer in req.candidate_answers if answer and answer.strip()]
    if not answers:
        return EvaluationResponse(score_dialog=0.0, explanation="Нет ответов")

    try:
        model = get_model()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Dialog scoring model is unavailable: {exc}") from exc

    job_text = " ".join(
        part.strip()
        for part in [req.vacancy_description, *req.hard_skills, *req.soft_skills]
        if part and part.strip()
    )
    embeddings = model.encode([job_text, *answers], normalize_embeddings=True)
    job_emb = embeddings[0]
    avg_answer_emb = np.mean(embeddings[1:], axis=0)
    similarity = float(np.clip(np.dot(job_emb, avg_answer_emb), -1.0, 1.0))
    score = float(np.clip((similarity + 1) / 2, 0.0, 1.0))

    return EvaluationResponse(score_dialog=score, explanation="Семантическая близость к требованиям")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
