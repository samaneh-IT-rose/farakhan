"""Declarative base plus model imports (Alembic target_metadata)."""
from app.db.base_class import Base

# Import all models so Base.metadata is complete
from app.db.models.location import Location  # noqa: E402, F401
from app.db.models.submission import Submission  # noqa: E402, F401
from app.db.models.submission_file import SubmissionFile  # noqa: E402, F401

__all__ = ["Base", "Location", "Submission", "SubmissionFile"]
