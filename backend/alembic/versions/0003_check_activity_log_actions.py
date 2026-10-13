"""Check activity_log.action in the database, and index the log by (course_id, id).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-14 00:26:34.680923

This reverses the step 2 choice to check actions only in code. activity_log is append-only, so a row
with a wrong action could never be corrected; now the database refuses it. The list is every action the
app writes; a future action needs a new migration that replaces this check.

The (course_id, id) index replaces the course_id index, because the feed reads one course's entries
ordered by id.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Written out rather than taken from app.models.Action: a migration must keep doing exactly the same
# thing even after the app's code changes.
ACTION_CHECK = (
    "action IN ('created', 'edited', 'lesson_added', 'lesson_edited', 'lessons_reordered', "
    "'lesson_removed', 'published', 'archived', 'restored', 'commented')"
)


def upgrade() -> None:
    op.create_check_constraint(op.f("ck_activity_log_action_allowed"), "activity_log", ACTION_CHECK)
    # Create the new index before dropping the old one, so the table is never without an index on course_id.
    op.create_index(op.f("ix_activity_log_course_id_id"), "activity_log", ["course_id", "id"])
    op.drop_index(op.f("ix_activity_log_course_id"), table_name="activity_log")


def downgrade() -> None:
    op.create_index(op.f("ix_activity_log_course_id"), "activity_log", ["course_id"])
    op.drop_index(op.f("ix_activity_log_course_id_id"), table_name="activity_log")
    op.drop_constraint(op.f("ck_activity_log_action_allowed"), "activity_log", type_="check")
