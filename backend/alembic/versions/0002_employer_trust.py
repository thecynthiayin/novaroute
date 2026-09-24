"""Employer verification, reports and administrator audit trail.

Revision ID: 0002_employer_trust
Revises: 0001_initial
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_employer_trust"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("student", "employer"),
        type_=sa.Enum("student", "employer", "admin"),
        existing_nullable=False,
    )
    for name, length in [
        ("legal_name", 200),
        ("registration_number", 150),
        ("registration_explanation", 1000),
        ("recruiter_name", 100),
        ("recruiter_position", 150),
        ("contact_email", 254),
        ("contact_phone", 80),
    ]:
        op.add_column(
            "employer_profiles", sa.Column(name, sa.String(length), nullable=False, server_default="")
        )
        op.alter_column("employer_profiles", name, existing_type=sa.String(length), server_default=None)
    op.add_column(
        "employer_profiles",
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.add_column(
        "employer_profiles",
        sa.Column("verification_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("employer_profiles", sa.Column("submitted_at", sa.DateTime(), nullable=True))
    op.add_column("employer_profiles", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("employer_profiles", sa.Column("review_reason", sa.Text(), nullable=True))
    op.execute("UPDATE employer_profiles SET review_reason = ''")
    op.alter_column("employer_profiles", "review_reason", existing_type=sa.Text(), nullable=False)
    op.alter_column(
        "employer_profiles", "verification_status", existing_type=sa.String(20), server_default=None
    )
    op.alter_column(
        "employer_profiles", "verification_version", existing_type=sa.Integer(), server_default=None
    )
    op.create_index("ix_employer_profiles_verification_status", "employer_profiles", ["verification_status"])
    op.add_column(
        "internships", sa.Column("admin_hidden", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.alter_column("internships", "admin_hidden", existing_type=sa.Boolean(), server_default=None)
    op.create_table(
        "listing_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("listing_id", sa.Integer(), sa.ForeignKey("internships.id"), nullable=False),
        sa.Column("reporter_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("listing_id", "reporter_id", name="uq_report_student_listing"),
    )
    for field in ("listing_id", "reporter_id", "status"):
        op.create_index("ix_listing_reports_" + field, "listing_reports", [field])
    op.create_table(
        "admin_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    # Refuse to silently turn privileged accounts into employers.
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT COUNT(*) FROM users WHERE role = 'admin'")):
        raise RuntimeError("Remove or explicitly reassign admin accounts before downgrading")
    op.drop_table("admin_audit")
    op.drop_table("listing_reports")
    op.drop_column("internships", "admin_hidden")
    op.drop_index("ix_employer_profiles_verification_status", "employer_profiles")
    for name in (
        "legal_name",
        "registration_number",
        "registration_explanation",
        "recruiter_name",
        "recruiter_position",
        "contact_email",
        "contact_phone",
        "verification_status",
        "verification_version",
        "submitted_at",
        "reviewed_at",
        "review_reason",
    ):
        op.drop_column("employer_profiles", name)
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("student", "employer", "admin"),
        type_=sa.Enum("student", "employer"),
        existing_nullable=False,
    )
