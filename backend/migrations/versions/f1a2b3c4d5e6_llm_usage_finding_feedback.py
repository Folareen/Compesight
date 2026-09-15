"""llm_usage, finding_feedback

Revision ID: f1a2b3c4d5e6
Revises: c02973847365
Create Date: 2026-09-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'c02973847365'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('llm_usage',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('purpose', sa.Enum('classification', 'extraction_fallback', 'battlecard', 'qa', name='llm_purpose'), nullable=False),
    sa.Column('model', sa.String(), nullable=False),
    sa.Column('input_tokens', sa.Integer(), nullable=False),
    sa.Column('output_tokens', sa.Integer(), nullable=False),
    sa.Column('cost_cents', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_usage_workspace_id'), 'llm_usage', ['workspace_id'], unique=False)
    op.create_index('ix_llm_usage_workspace_created_at', 'llm_usage', ['workspace_id', 'created_at'], unique=False)

    op.create_table('finding_feedback',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('finding_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('verdict', sa.Enum('useful', 'noise', name='feedback_verdict'), nullable=False),
    sa.Column('corrected_change_type', postgresql.ENUM('pricing', 'feature_launch', 'messaging', 'hiring', 'funding', 'partnership', 'content', 'other', name='change_type', create_type=False), nullable=True),
    sa.Column('corrected_urgency', postgresql.ENUM('high', 'medium', 'low', name='urgency', create_type=False), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['finding_id'], ['finding.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_finding_feedback_workspace_id'), 'finding_feedback', ['workspace_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_finding_feedback_workspace_id'), table_name='finding_feedback')
    op.drop_table('finding_feedback')
    sa.Enum(name='feedback_verdict').drop(op.get_bind(), checkfirst=True)

    op.drop_index('ix_llm_usage_workspace_created_at', table_name='llm_usage')
    op.drop_index(op.f('ix_llm_usage_workspace_id'), table_name='llm_usage')
    op.drop_table('llm_usage')
    sa.Enum(name='llm_purpose').drop(op.get_bind(), checkfirst=True)
