from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Submission(Base):
	__tablename__ = "submissions"

	submission_id: Mapped[str] = mapped_column(
		String(36),
		primary_key=True,
		default=lambda: str(uuid4()),
	)
	assignment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
	attempt_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
	user_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
	resource_link_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
	status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
	score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
	max_points: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
	feedback_stdout: Mapped[str] = mapped_column(Text, nullable=False, default="")
	feedback_stderr: Mapped[str] = mapped_column(Text, nullable=False, default="")
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
		default=lambda: datetime.now(timezone.utc),
	)
	completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
