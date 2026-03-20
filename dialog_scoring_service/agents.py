from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass


TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "")]


@dataclass(slots=True)
class RetrievedChunk:
    text: str
    score: float
    source: str


class VacancyRAG:
    def build_chunks(self, vacancy_description: str, hard_skills: list[str], soft_skills: list[str]) -> list[dict[str, str]]:
        chunks: list[dict[str, str]] = []
        if vacancy_description.strip():
            chunks.append({"source": "vacancy_description", "text": vacancy_description.strip()})
        for skill in hard_skills:
            if skill.strip():
                chunks.append({"source": "hard_skill", "text": skill.strip()})
        for skill in soft_skills:
            if skill.strip():
                chunks.append({"source": "soft_skill", "text": skill.strip()})
        return chunks

    def retrieve(self, chunks: list[dict[str, str]], query: str, *, top_k: int = 3) -> list[RetrievedChunk]:
        query_tokens = Counter(tokenize(query))
        if not query_tokens:
            return []

        scored: list[RetrievedChunk] = []
        for chunk in chunks:
            chunk_tokens = Counter(tokenize(chunk["text"]))
            if not chunk_tokens:
                continue
            overlap = sum(min(query_tokens[token], chunk_tokens[token]) for token in query_tokens)
            if overlap == 0:
                continue
            norm = math.sqrt(sum(query_tokens.values())) * math.sqrt(sum(chunk_tokens.values()))
            score = overlap / norm if norm else 0.0
            scored.append(RetrievedChunk(text=chunk["text"], score=round(score, 4), source=chunk["source"]))

        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]


class RetrieverAgent:
    def __init__(self, rag: VacancyRAG | None = None) -> None:
        self.rag = rag or VacancyRAG()

    def run(self, vacancy_description: str, hard_skills: list[str], soft_skills: list[str], candidate_answers: list[str]) -> list[RetrievedChunk]:
        chunks = self.rag.build_chunks(vacancy_description, hard_skills, soft_skills)
        query = " ".join(candidate_answers)
        return self.rag.retrieve(chunks, query)


class ScoringAgent:
    def __init__(self, scorer) -> None:
        self.scorer = scorer

    def run(self, job_text: str, candidate_answers: list[str]) -> tuple[float, dict]:
        return self.scorer.score(job_text, candidate_answers)


class ScreeningCoordinatorAgent:
    def __init__(self, retriever: RetrieverAgent, scorer: ScoringAgent) -> None:
        self.retriever = retriever
        self.scorer = scorer

    def run(
        self,
        *,
        vacancy_description: str,
        hard_skills: list[str],
        soft_skills: list[str],
        candidate_answers: list[str],
    ) -> dict:
        job_text = " ".join([vacancy_description, *hard_skills, *soft_skills]).strip()
        evidence = self.retriever.run(vacancy_description, hard_skills, soft_skills, candidate_answers)
        score, debug = self.scorer.run(job_text, candidate_answers)
        return {
            "score_dialog": score,
            "evidence": [{"text": item.text, "score": item.score, "source": item.source} for item in evidence],
            "debug": debug,
        }
