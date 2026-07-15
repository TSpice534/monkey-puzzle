import secrets
from datetime import datetime, timezone
from typing import Optional

from app import db


class Submission(db.Model):
    id: db.Mapped[int] = db.mapped_column(primary_key=True)
    token: db.Mapped[str] = db.mapped_column(
        db.String(43), unique=True, index=True, nullable=False,
        default=lambda: secrets.token_urlsafe(32)
    )
    # Raw answers keyed by question id (empty in Phase 1; populated in Phase 3)
    answers: db.Mapped[dict] = db.mapped_column(db.JSON, nullable=False, default=dict)
    # 'individual' | 'organisation' — set from the survey's respondent-type
    # router question (its answer also lives in `answers` like any other
    # question); unset until that question is answered. Determines which
    # audience-tagged questions are shown for the rest of the survey.
    audience: db.Mapped[Optional[str]] = db.mapped_column(db.String(16), nullable=True)
    # Classification result — unset until Phase 4
    persona_id: db.Mapped[Optional[str]] = db.mapped_column(db.String(32), nullable=True)
    # Nine-dim persona vector — unset until Phase 4
    score_vector: db.Mapped[Optional[dict]] = db.mapped_column(db.JSON, nullable=True)
    # Rogers' innovation-curve result (backlog #0002) — unset until the survey completes;
    # None for surveys with no `innovation_curve` config (e.g. test fixtures).
    innovation_band: db.Mapped[Optional[str]] = db.mapped_column(db.String(32), nullable=True)
    innovation_score: db.Mapped[Optional[int]] = db.mapped_column(db.Integer, nullable=True)
    created_at: db.Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True),
        index=True,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: db.Mapped[datetime] = db.mapped_column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f'<Submission {self.id} persona={self.persona_id}>'
