from __future__ import annotations

import io
import zipfile


def create_vacancy(client):
    response = client.post(
        "/api/vacancies",
        json={
            "title": "Python Backend Engineer",
            "description": "Нужен инженер с FastAPI и PostgreSQL.",
            "hard_skills": ["Python", "FastAPI", "PostgreSQL"],
            "soft_skills": ["Communication"],
            "seniority": "Middle",
            "status": "active",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload_candidate(client, vacancy_id, sample_docx_bytes):
    response = client.post(
        f"/api/vacancies/{vacancy_id}/resumes/upload",
        files={"file": ("candidate.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"consent_to_personal_data_processing": "true"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_happy_path_create_upload_email_outreach_and_telegram_start(client, sample_docx_bytes):
    vacancy = create_vacancy(client)
    upload_payload = upload_candidate(client, vacancy["id"], sample_docx_bytes)
    assert upload_payload["processed"] == 1

    candidates_response = client.get(f"/api/vacancies/{vacancy['id']}/candidates")
    assert candidates_response.status_code == 200
    candidates = candidates_response.json()
    assert len(candidates) == 1
    candidate_id = candidates[0]["candidate_id"]
    assert candidates[0]["contact_status"] == "email_invite_pending"

    outreach_response = client.post(
        f"/api/vacancies/{vacancy['id']}/send-invites",
        json={"top_n": 1, "refresh_invite_token": False},
    )
    assert outreach_response.status_code == 200, outreach_response.text
    outreach = outreach_response.json()
    assert outreach["sent"] == 1

    candidate_response = client.get(f"/api/candidates/{candidate_id}")
    assert candidate_response.status_code == 200
    candidate = candidate_response.json()
    assert candidate["contact_status"] == "awaiting_candidate_start"
    assert candidate["invite_token_created_at"] is not None


def test_telegram_webhook_connects_candidate(client, sample_docx_bytes):
    vacancy = create_vacancy(client)
    upload_candidate(client, vacancy["id"], sample_docx_bytes)
    client.post(f"/api/vacancies/{vacancy['id']}/send-invites", json={"top_n": 1, "refresh_invite_token": False})
    candidate = client.get("/api/vacancies/1/candidates").json()[0]

    from app.db.session import SessionLocal
    from app.models.candidate import Candidate

    with SessionLocal() as db:
        token = db.get(Candidate, candidate["candidate_id"]).invite_token

    response = client.post(
        "/api/telegram/webhook",
        json={
            "message": {
                "text": f"/start {token}",
                "chat": {"id": 777001},
                "from": {"username": "ivan_candidate"},
            }
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["event"] == "telegram_connected"

    updated = client.get(f"/api/candidates/{candidate['candidate_id']}").json()
    assert updated["telegram_chat_id"] == "777001"
    assert updated["contact_status"] in {"telegram_connected", "screening_in_progress"}


def test_broken_zip_returns_error(client):
    vacancy = create_vacancy(client)
    response = client.post(
        f"/api/vacancies/{vacancy['id']}/resumes/upload",
        files={"file": ("broken.zip", b"not-a-zip", "application/zip")},
        data={"consent_to_personal_data_processing": "true"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSAFE_ARCHIVE"


def test_unsupported_file_returns_error(client):
    vacancy = create_vacancy(client)
    response = client.post(
        f"/api/vacancies/{vacancy['id']}/resumes/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        data={"consent_to_personal_data_processing": "true"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE"


def test_empty_resume_marked_as_failed(client, empty_docx_bytes):
    vacancy = create_vacancy(client)
    response = client.post(
        f"/api/vacancies/{vacancy['id']}/resumes/upload",
        files={"file": ("empty.docx", empty_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"consent_to_personal_data_processing": "true"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["skipped_empty"] == 1


def test_invalid_llm_response_marks_resume_failed(client, sample_docx_bytes, monkeypatch):
    class BrokenLLMClient:
        async def complete_json(self, prompt, json_schema, *, temperature=0.0):
            raise ValueError("invalid llm response")

    monkeypatch.setattr("app.services.candidate_extractor.get_llm_client", lambda: BrokenLLMClient())
    monkeypatch.setattr("app.services.scoring.get_llm_client", lambda: BrokenLLMClient())

    vacancy = create_vacancy(client)
    response = client.post(
        f"/api/vacancies/{vacancy['id']}/resumes/upload",
        files={"file": ("candidate.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"consent_to_personal_data_processing": "true"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["parse_failed"] == 1


def test_zip_with_nested_docx_is_processed(client, sample_docx_bytes):
    vacancy = create_vacancy(client)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("nested/folder/candidate.docx", sample_docx_bytes)

    response = client.post(
        f"/api/vacancies/{vacancy['id']}/resumes/upload",
        files={"file": ("batch.zip", buffer.getvalue(), "application/zip")},
        data={"consent_to_personal_data_processing": "true"},
    )
    assert response.status_code == 200
    assert response.json()["processed"] == 1
