from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.core.exceptions import ArchiveSecurityError
from app.services.file_service import FileService


def test_zip_slip_is_rejected(tmp_path: Path):
    settings = get_settings()
    settings.uploads_dir = tmp_path / "uploads"
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)

    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../evil.docx", b"bad")

    service = FileService()
    with pytest.raises(ArchiveSecurityError):
        service.extract_resumes(archive_path)
