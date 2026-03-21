from __future__ import annotations

import json
import os
import re
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
TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


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

    def score(self, job_text: str, candidate_answers: list[str], *, evidence: list | None = None) -> tuple[float, dict]:
        answers = [answer.strip() for answer in candidate_answers if answer and answer.strip()][:MAX_ANSWERS]
        if not answers:
            return 0.0, {"mode": "empty"}

        embeddings = self.model.encode([job_text, *answers], normalize_embeddings=True)
        job_emb = embeddings[0]
        avg_answer_emb = np.mean(embeddings[1:], axis=0)
        similarity = float(np.clip(np.dot(job_emb, avg_answer_emb), -1.0, 1.0))
        base_score = float(np.clip((similarity + 1.0) / 2.0, 0.0, 1.0))
        lexical_overlap = self._lexical_overlap(job_text, answers)
        diversity = self._answer_diversity(answers)
        richness = self._answer_richness(answers)
        evidence_support = self._evidence_support(evidence or [])
        combined_score = float(
            np.clip(
                base_score * 0.45 + lexical_overlap * 0.2 + diversity * 0.15 + richness * 0.1 + evidence_support * 0.1,
                0.0,
                1.0,
            )
        )

        if not self.calibrator:
            return combined_score, {
                "mode": "embedding+heuristics",
                "similarity": round(similarity, 4),
                "lexical_overlap": round(lexical_overlap, 4),
                "diversity": round(diversity, 4),
                "richness": round(richness, 4),
                "evidence_support": round(evidence_support, 4),
            }

        avg_answer_len = sum(len(answer.split()) for answer in answers) / len(answers)
        calibrated = self.calibrator.apply([combined_score, len(answers) / MAX_ANSWERS, min(avg_answer_len / 40.0, 1.0)])
        calibrated_score = float(np.clip(calibrated, 0.0, 1.0))
        return calibrated_score, {
            "mode": "calibrated",
            "similarity": round(similarity, 4),
            "lexical_overlap": round(lexical_overlap, 4),
            "diversity": round(diversity, 4),
            "richness": round(richness, 4),
            "evidence_support": round(evidence_support, 4),
        }

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text or "")]

    def _lexical_overlap(self, job_text: str, answers: list[str]) -> float:
        job_tokens = set(self._tokenize(job_text))
        answer_tokens = set(self._tokenize(" ".join(answers)))
        if not job_tokens:
            return 0.0
        return len(job_tokens & answer_tokens) / len(job_tokens)

    def _answer_diversity(self, answers: list[str]) -> float:
        tokens = self._tokenize(" ".join(answers))
        if not tokens:
            return 0.0
        return len(set(tokens)) / len(tokens)

    @staticmethod
    def _answer_richness(answers: list[str]) -> float:
        avg_len = sum(len(answer.split()) for answer in answers) / max(len(answers), 1)
        return min(avg_len / 18.0, 1.0)

    @staticmethod
    def _evidence_support(evidence: list) -> float:
        if not evidence:
            return 0.0
        top_score = max(float(getattr(item, "score", 0.0)) for item in evidence)
        return min(top_score, 1.0)
