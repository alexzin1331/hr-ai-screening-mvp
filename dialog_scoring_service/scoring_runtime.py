from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_NAME = os.getenv("DIALOG_SCORING_MODEL_NAME", "intfloat/multilingual-e5-small")
CALIBRATOR_PATH = Path(os.getenv("DIALOG_SCORING_CALIBRATOR_PATH", ROOT_DIR / "artifacts" / "soft_skills_calibrator.json"))
MAX_ANSWERS = max(1, int(os.getenv("DIALOG_SCORING_MAX_ANSWERS", "8")))
TORCH_THREADS = max(1, int(os.getenv("DIALOG_SCORING_THREADS", "2")))


@dataclass(slots=True)
class LinearCalibrator:
    weights: list[float]
    bias: float

    def apply(self, features: list[float]) -> float:
        return float(sum(weight * feature for weight, feature in zip(self.weights, features)) + self.bias)


def configure_runtime() -> None:
    if torch is not None:
        torch.set_num_threads(TORCH_THREADS)
        torch.set_num_interop_threads(1)


@lru_cache
def get_model():
    configure_runtime()
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers is not installed")
    return SentenceTransformer(DEFAULT_MODEL_NAME, device="cpu")


@lru_cache
def get_calibrator() -> LinearCalibrator | None:
    if not CALIBRATOR_PATH.exists():
        return None
    payload = json.loads(CALIBRATOR_PATH.read_text(encoding="utf-8"))
    return LinearCalibrator(weights=list(payload["weights"]), bias=float(payload["bias"]))


class LocalEmbeddingScorer:
    def __init__(self) -> None:
        self.model = get_model()
        self.calibrator = get_calibrator()

    def score(self, job_text: str, candidate_answers: list[str]) -> tuple[float, dict]:
        answers = [answer.strip() for answer in candidate_answers if answer and answer.strip()][:MAX_ANSWERS]
        if not answers:
            return 0.0, {"mode": "empty"}

        embeddings = self.model.encode([job_text, *answers], normalize_embeddings=True)
        job_emb = embeddings[0]
        avg_answer_emb = np.mean(embeddings[1:], axis=0)
        similarity = float(np.clip(np.dot(job_emb, avg_answer_emb), -1.0, 1.0))
        base_score = float(np.clip((similarity + 1.0) / 2.0, 0.0, 1.0))

        if not self.calibrator:
            return base_score, {"mode": "embedding", "similarity": round(similarity, 4)}

        avg_answer_len = sum(len(answer.split()) for answer in answers) / len(answers)
        calibrated = self.calibrator.apply([base_score, len(answers) / MAX_ANSWERS, min(avg_answer_len / 40.0, 1.0)])
        calibrated_score = float(np.clip(calibrated, 0.0, 1.0))
        return calibrated_score, {"mode": "calibrated", "similarity": round(similarity, 4)}
