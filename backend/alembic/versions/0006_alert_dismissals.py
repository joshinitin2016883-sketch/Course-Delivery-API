"""Create the alert_dismissals table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-15 12:58:21.000000

An instructor dismisses an inactivity alert for one quiet spell: quiet_since is the enrolment's last_activity_at
at the time. The database allows one dismissal per spell (unique on enrollment_id and quiet_since), so two
instructors dismissing at the same moment can't both record one.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_dismissals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("quiet_since", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dismissed_by", sa.Integer(), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["enrollments.id"], name=op.f("fk_alert_dismissals_enrollment_id_enrollments")
        ),
        sa.ForeignKeyConstraint(["dismissed_by"], ["users.id"], name=op.f("fk_alert_dismissals_dismissed_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_dismissals")),
        sa.UniqueConstraint("enrollment_id", "quiet_since", name="uq_alert_dismissals_enrollment_id_quiet_since"),
    )


def downgrade() -> None:
    op.drop_table("alert_dismissals")
