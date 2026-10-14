"""Index lesson_completions by lesson_id.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-14 09:45:12.288506

Removing a lesson first asks "has any learner completed this lesson?", and the RESTRICT foreign key asks
the same when the row is deleted. Without this index both would scan the whole table.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_lesson_completions_lesson_id"), "lesson_completions", ["lesson_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_lesson_completions_lesson_id"), table_name="lesson_completions")
