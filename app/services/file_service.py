from __future__ import annotations

import logging
import os
import shutil
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import ArchiveSecurityError, ValidationAppError


logger = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".zip"}
RESUME_EXTENSIONS = {".pdf", ".docx"}


@dataclass(slots=True)
class StoredFile:
    original_name: str
    stored_name: str
    path: Path
    file_type: str


class FileService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.last_skipped_unsupported = 0

    def save_upload(self, file: UploadFile) -> StoredFile:
        extension = Path(file.filename or "").suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValidationAppError("UNSUPPORTED_FILE", "Unsupported uploaded file format", {"file_name": file.filename})

        batch_id = str(uuid.uuid4())
        target_dir = self.settings.uploads_dir / "incoming" / batch_id
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}{extension}"
        path = target_dir / safe_name

        logger.info("Saving uploaded file name=%s path=%s", file.filename, path)
        with path.open("wb") as target:
            shutil.copyfileobj(file.file, target)

        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > self.settings.max_upload_size_mb:
            path.unlink(missing_ok=True)
            raise ValidationAppError(
                "UPLOAD_TOO_LARGE",
                "Uploaded file exceeds configured size limit",
                {"max_upload_size_mb": self.settings.max_upload_size_mb},
            )

        return StoredFile(
            original_name=file.filename or safe_name,
            stored_name=safe_name,
            path=path,
            file_type=extension.removeprefix("."),
        )

    def extract_resumes(self, archive_path: Path) -> list[StoredFile]:
        extract_root = self.settings.uploads_dir / "extracted" / archive_path.stem
        extract_root.mkdir(parents=True, exist_ok=True)
        total_uncompressed = 0
        extracted: list[StoredFile] = []
        skipped_unsupported = 0

        try:
            zip_ref = zipfile.ZipFile(archive_path)
        except zipfile.BadZipFile as exc:
            raise ArchiveSecurityError("Uploaded archive is corrupted", {"file_name": archive_path.name}) from exc

        with zip_ref:
            members = zip_ref.infolist()
            if len(members) > self.settings.zip_max_members:
                raise ArchiveSecurityError("Archive contains too many files", {"members": len(members)})

            for member in members:
                if member.is_dir():
                    continue

                original = member.filename
                self._validate_member(member.filename)
                total_uncompressed += member.file_size
                if total_uncompressed > self.settings.zip_max_total_size_mb * 1024 * 1024:
                    raise ArchiveSecurityError("Archive is too large after extraction")

                extension = Path(original).suffix.lower()
                if extension not in RESUME_EXTENSIONS:
                    logger.warning("Skipping unsupported file inside zip file=%s", original)
                    skipped_unsupported += 1
                    continue

                stored_name = f"{uuid.uuid4().hex}{extension}"
                destination = extract_root / stored_name
                with zip_ref.open(member, "r") as source, destination.open("wb") as target:
                    self._copy_stream(source, target)
                extracted.append(
                    StoredFile(
                        original_name=Path(original).name,
                        stored_name=stored_name,
                        path=destination,
                        file_type=extension.removeprefix("."),
                    )
                )
                logger.info("Extracted zip member original=%s stored=%s", original, destination)

        self.last_skipped_unsupported = skipped_unsupported
        return extracted

    def collect_resume_files(self, stored_file: StoredFile) -> list[StoredFile]:
        if Path(stored_file.original_name).suffix.lower() in RESUME_EXTENSIONS:
            self.last_skipped_unsupported = 0
            return [stored_file]
        return self.extract_resumes(stored_file.path)

    def _validate_member(self, name: str) -> None:
        normalized = Path(name)
        if normalized.is_absolute():
            raise ArchiveSecurityError("Archive contains absolute paths", {"member": name})
        if ".." in normalized.parts:
            raise ArchiveSecurityError("Archive contains unsafe path traversal", {"member": name})
        if name.startswith("/") or name.startswith("\\"):
            raise ArchiveSecurityError("Archive member path is unsafe", {"member": name})

    @staticmethod
    def _copy_stream(source: BinaryIO, target: BinaryIO) -> None:
        shutil.copyfileobj(source, target, length=1024 * 1024)
