from __future__ import annotations

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents import RetrieverAgent, ScoringAgent, ScreeningCoordinatorAgent
from scoring_runtime import DEFAULT_MODEL_NAME, LocalEmbeddingScorer, get_model


app = FastAPI(title="Dialog Scoring Service")


class EvaluationRequest(BaseModel):
    vacancy_description: str
    hard_skills: list[str]
    soft_skills: list[str]
    candidate_answers: list[str]


class EvaluationResponse(BaseModel):
    score_dialog: float
    explanation: str = ""


@app.get("/health")
def health() -> dict[str, str]:
    try:
        get_model()
        return {"status": "ok", "model": DEFAULT_MODEL_NAME, "inference_mode": "local"}
    except Exception as exc:
        return {"status": "degraded", "model": DEFAULT_MODEL_NAME, "error": str(exc), "inference_mode": "local"}


@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(req: EvaluationRequest) -> EvaluationResponse:
    answers = [answer.strip() for answer in req.candidate_answers if answer and answer.strip()]
    if not answers:
        return EvaluationResponse(score_dialog=0.0, explanation="Нет ответов")

    try:
        coordinator = ScreeningCoordinatorAgent(
            retriever=RetrieverAgent(),
            scorer=ScoringAgent(LocalEmbeddingScorer()),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Dialog scoring model is unavailable: {exc}") from exc

    result = coordinator.run(
        vacancy_description=req.vacancy_description,
        hard_skills=req.hard_skills,
        soft_skills=req.soft_skills,
        candidate_answers=answers,
    )
    evidence = result["evidence"]
    evidence_suffix = f" Топ-контекст: {evidence[0]['text']}" if evidence else ""
    return EvaluationResponse(
        score_dialog=result["score_dialog"],
        explanation=f"Локальный multi-agent scoring по релевантным требованиям.{evidence_suffix}",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
