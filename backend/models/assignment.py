from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Assignment(Base):
	__tablename__ = "assignments"

	assignment_id: Mapped[str] = mapped_column(
		String(36),
		primary_key=True,
		default=lambda: str(uuid4()),
	)
	instructor_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
	course_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
	resource_link_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
	lineitem_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
	title: Mapped[str] = mapped_column(String(255), nullable=False)
	instructions: Mapped[str] = mapped_column(Text, nullable=False)
	due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	max_points: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
	is_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
	grading_feature: Mapped[str] = mapped_column(String(64), nullable=False, default="script_zip")
	grading_config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
	starter_zip_path: Mapped[str | None] = mapped_column(Text, nullable=True)
	tests_zip_path: Mapped[str | None] = mapped_column(Text, nullable=True)
	starter_extracted_path: Mapped[str | None] = mapped_column(Text, nullable=True)
	tests_extracted_path: Mapped[str | None] = mapped_column(Text, nullable=True)
	has_required_test_runner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	artifacts_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	artifact_validation_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
		default=lambda: datetime.now(timezone.utc),
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
		default=lambda: datetime.now(timezone.utc),
		onupdate=lambda: datetime.now(timezone.utc),
	)
