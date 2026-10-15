"""Exporting a course's progress as a CSV file (goal 7).

The rows come from enrollment_service.course_progress, so the file always matches the Enrolled learners
list: the same learners in the same order, under the same rule (instructors only). Draft and archived
courses can still be exported, because their history is kept.
"""
import csv
import io
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import User
from app.services import enrollment_service

COLUMNS = [
    "name",
    "email",
    "status",
    "lessons_done",
    "lessons_total",
    "enrolled_at",
    "started_at",
    "completed_at",
    "last_activity_at",
]
# A spreadsheet runs a cell that starts with one of these as a formula. Names are typed by people and the file
# is made to be opened in Excel, so such a cell gets a leading apostrophe and shows as plain text instead.
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def progress_csv(db: Session, viewer: User, course_id: int) -> tuple[str, str]:
    """The CSV text, and the name to save it under: course-<id>-progress-<today's UTC date>.csv."""
    learners = enrollment_service.course_progress(db, viewer, course_id)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(COLUMNS)
    for row in learners:
        writer.writerow([
            _cell(row.learner.full_name),
            _cell(row.learner.email),
            _cell(row.status),
            row.lessons_done,
            row.lessons_total,
            _time(row.enrolled_at),
            _time(row.started_at),
            _time(row.completed_at),
            _time(row.last_activity_at),
        ])
    filename = f"course-{course_id}-progress-{datetime.now(timezone.utc).date().isoformat()}.csv"
    return filename, out.getvalue()


def _cell(text: str) -> str:
    if text.startswith(FORMULA_STARTS):
        return "'" + text
    return text


def _time(moment: datetime | None) -> str:
    """ISO 8601 in UTC to the second, such as 2026-10-15T08:53:00Z; empty when it hasn't happened yet."""
    if moment is None:
        return ""
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
