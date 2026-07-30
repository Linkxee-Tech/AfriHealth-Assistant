"""Create the initial AfriHealth schema.

The application keeps its compatibility checks in DatabaseManager for old
SQLite installations, while fresh deployments can use this Alembic revision
as the explicit schema baseline.
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "password_resets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])
    op.create_index("ix_password_resets_token_hash", "password_resets", ["token_hash"], unique=True)

    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("mrn", sa.String(20)),
        sa.Column("first_name", sa.String(50)),
        sa.Column("last_name", sa.String(50)),
        sa.Column("gender", sa.String(10)),
        sa.Column("date_of_birth", sa.DateTime()),
        sa.Column("phone", sa.String(20)),
        sa.Column("emergency_contact", sa.String(100)),
        sa.Column("address", sa.String(200)),
        sa.Column("blood_type", sa.String(5)),
        sa.Column("allergies", sa.Text()),
        sa.Column("medical_history", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_patients_user_id", "patients", ["user_id"])
    op.create_index("ix_patients_mrn", "patients", ["mrn"], unique=True)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("session_id", sa.String(50), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_conversations_session_id", "conversations", ["session_id"], unique=True)

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", sa.Text()),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "health_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("metric_type", sa.String(50), nullable=False),
        sa.Column("value", sa.String(100), nullable=False),
        sa.Column("unit", sa.String(20)),
        sa.Column("notes", sa.Text()),
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(50)),
        sa.Column("content", sa.Text()),
        sa.Column("analysis_result", sa.Text()),
        sa.Column("char_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("chunk_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("chunks_added_to_rag", sa.Integer(), server_default=sa.text("0")),
        sa.Column("uploaded_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "visits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id")),
        sa.Column("visit_date", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("visit_type", sa.String(50)),
        sa.Column("chief_complaint", sa.Text()),
        sa.Column("history", sa.Text()),
        sa.Column("examination", sa.Text()),
        sa.Column("diagnosis", sa.Text()),
        sa.Column("ai_suggestions", sa.Text()),
        sa.Column("medications", sa.Text()),
        sa.Column("tests", sa.Text()),
        sa.Column("referral", sa.Text()),
        sa.Column("next_visit", sa.DateTime()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "prescriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("visit_id", sa.Integer(), sa.ForeignKey("visits.id")),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id")),
        sa.Column("medication", sa.String(100)),
        sa.Column("dosage", sa.String(50)),
        sa.Column("frequency", sa.String(50)),
        sa.Column("duration", sa.String(50)),
        sa.Column("prescribed_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "clinical_guidelines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "drugs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("dosage_info", sa.Text()),
        sa.Column("side_effects", sa.Text()),
        sa.Column("contraindications", sa.Text()),
        sa.Column("interactions", sa.Text()),
    )
    op.create_index("ix_drugs_name", "drugs", ["name"], unique=True)
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(50), nullable=False),
        sa.Column("value", sa.Text()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_settings_key", "settings", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_settings_key", table_name="settings")
    op.drop_table("settings")
    op.drop_index("ix_drugs_name", table_name="drugs")
    op.drop_table("drugs")
    op.drop_table("clinical_guidelines")
    op.drop_table("prescriptions")
    op.drop_table("visits")
    op.drop_table("documents")
    op.drop_table("health_metrics")
    op.drop_table("messages")
    op.drop_index("ix_conversations_session_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_patients_mrn", table_name="patients")
    op.drop_index("ix_patients_user_id", table_name="patients")
    op.drop_table("patients")
    op.drop_index("ix_password_resets_token_hash", table_name="password_resets")
    op.drop_index("ix_password_resets_user_id", table_name="password_resets")
    op.drop_table("password_resets")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
