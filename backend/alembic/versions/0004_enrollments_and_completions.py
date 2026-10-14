"""Create the enrollments and lesson_completions tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-14 09:07:13.287067

The database itself enforces:
- one enrolment per learner per course, and one completion per lesson per enrolment;
- an enrolment's status and its times always agree (completed exactly when completed_at is set,
  not_started exactly when started_at is empty, and a last activity time exactly when started);
- a lesson that any learner has completed can't be deleted (RESTRICT).
The allowed values are written out here rather than taken from the app's code, so this migration
keeps doing exactly the same thing even after the code changes.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="not_started", nullable=False),
        sa.Column("enrolled_by", sa.Integer(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')", name=op.f("ck_enrollments_status_allowed")
        ),
        sa.CheckConstraint(
            "(status = 'completed') = (completed_at IS NOT NULL)",
            name=op.f("ck_enrollments_completed_matches_completed_at"),
        ),
        sa.CheckConstraint(
            "(status = 'not_started') = (started_at IS NULL)",
            name=op.f("ck_enrollments_not_started_matches_started_at"),
        ),
        sa.CheckConstraint(
            "(started_at IS NULL) = (last_activity_at IS NULL)",
            name=op.f("ck_enrollments_started_matches_last_activity"),
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_enrollments_course_id_courses")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_enrollments_user_id_users")),
        sa.ForeignKeyConstraint(["enrolled_by"], ["users.id"], name=op.f("fk_enrollments_enrolled_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enrollments")),
        sa.UniqueConstraint("course_id", "user_id", name="uq_enrollments_course_id_user_id"),
    )
    op.create_index("ix_enrollments_user_id", "enrollments", ["user_id"])
    op.create_index("ix_enrollments_course_id_status", "enrollments", ["course_id", "status"])

    op.create_table(
        "lesson_completions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["enrollments.id"], name=op.f("fk_lesson_completions_enrollment_id_enrollments")
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"], ["lessons.id"], name=op.f("fk_lesson_completions_lesson_id_lessons"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lesson_completions")),
        sa.UniqueConstraint("enrollment_id", "lesson_id", name="uq_lesson_completions_enrollment_id_lesson_id"),
    )


def downgrade() -> None:
    op.drop_table("lesson_completions")
    op.drop_index("ix_enrollments_course_id_status", table_name="enrollments")
    op.drop_index("ix_enrollments_user_id", table_name="enrollments")
    op.drop_table("enrollments")
