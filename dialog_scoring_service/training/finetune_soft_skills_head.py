from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from dialog_scoring_service.scoring_runtime import DEFAULT_MODEL_NAME, LocalEmbeddingScorer, get_model


def extract_features(record: dict) -> list[float]:
    answers = [answer.strip() for answer in record["candidate_answers"] if answer and answer.strip()]
    job_text = " ".join([record["vacancy_description"], *record.get("hard_skills", []), *record.get("soft_skills", [])]).strip()
    embeddings = get_model().encode([job_text, *answers], normalize_embeddings=True)
    similarity = float(np.clip(np.dot(embeddings[0], np.mean(embeddings[1:], axis=0)), -1.0, 1.0))
    base_score = float(np.clip((similarity + 1.0) / 2.0, 0.0, 1.0))
    avg_answer_len = sum(len(answer.split()) for answer in answers) / max(len(answers), 1)
    return [base_score, len(answers) / 8.0, min(avg_answer_len / 40.0, 1.0)]


def fit_linear_head(dataset: list[dict]) -> dict:
    x = np.array([extract_features(record) + [1.0] for record in dataset], dtype=float)
    y = np.array([float(record["label"]) for record in dataset], dtype=float)
    solution, *_ = np.linalg.lstsq(x, y, rcond=None)
    return {
        "model_name": DEFAULT_MODEL_NAME,
        "weights": solution[:-1].round(6).tolist(),
        "bias": round(float(solution[-1]), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a lightweight soft-skills scoring head on top of local embeddings.")
    parser.add_argument("--dataset", required=True, help="Path to JSONL dataset with label in range 0..1")
    parser.add_argument("--output", required=True, help="Where to save the trained calibrator JSON")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    output_path = Path(args.output)
    rows = [json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    calibrator = fit_linear_head(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(calibrator, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved calibrator to {output_path}")


if __name__ == "__main__":
    main()
