"""Create the courses, lessons and activity_log tables, and make activity_log append-only.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13 08:26:48.682960

The database itself enforces: course status and category come from fixed lists; a lesson's position
is at least 1 and unique within its course (checked at commit, so lessons can be renumbered in one
transaction); and activity_log rows can never be updated, deleted or truncated.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# One function, used by two triggers: it refuses whatever operation fired it.
CREATE_REJECT_FUNCTION = """
CREATE FUNCTION reject_activity_log_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'activity_log is append-only: rows cannot be changed or deleted';
END;
$$
"""


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("instructor_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "category IN ('onboarding', 'compliance', 'skills')", name=op.f("ck_courses_category_allowed")
        ),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name=op.f("ck_courses_status_allowed")),
        sa.ForeignKeyConstraint(["instructor_id"], ["users.id"], name=op.f("fk_courses_instructor_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
    )

    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("position >= 1", name=op.f("ck_lessons_position_positive")),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_lessons_course_id_courses")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lessons")),
        sa.UniqueConstraint(
            "course_id", "position", name="uq_lessons_course_id_position", deferrable=True, initially="DEFERRED"
        ),
    )

    op.create_table(
        "activity_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], name=op.f("fk_activity_log_actor_id_users")),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_activity_log_course_id_courses")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_log")),
    )
    op.create_index(op.f("ix_activity_log_course_id"), "activity_log", ["course_id"])

    # Append-only: reject UPDATE and DELETE on any row, and TRUNCATE of the whole table.
    op.execute(CREATE_REJECT_FUNCTION)
    op.execute(
        "CREATE TRIGGER activity_log_no_update_or_delete BEFORE UPDATE OR DELETE ON activity_log "
        "FOR EACH ROW EXECUTE FUNCTION reject_activity_log_change()"
    )
    op.execute(
        "CREATE TRIGGER activity_log_no_truncate BEFORE TRUNCATE ON activity_log "
        "FOR EACH STATEMENT EXECUTE FUNCTION reject_activity_log_change()"
    )


def downgrade() -> None:
    # Dropping the table also drops its triggers; the function goes after.
    op.drop_index(op.f("ix_activity_log_course_id"), table_name="activity_log")
    op.drop_table("activity_log")
    op.execute("DROP FUNCTION reject_activity_log_change()")
    op.drop_table("lessons")
    op.drop_table("courses")
