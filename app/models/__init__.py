"""ORM-модели.

Импорт всех ORM-классов здесь нужен, чтобы SQLAlchemy видел связанные
relationship-имена до конфигурации mapper'ов.
"""

from app.models.audit_log import AuditLog
from app.models.candidate import Candidate
from app.models.resume import Resume
from app.models.scoring import Scoring
from app.models.screening_session import ScreeningSession
from app.models.user import User
from app.models.vacancy import Vacancy

__all__ = [
    "User",
    "Vacancy",
    "Candidate",
    "Resume",
    "Scoring",
    "ScreeningSession",
    "AuditLog",
]
