"""Add start_time and end_time to clips table

Task 2.5.2: Fix clip time semantics
Store absolute media timestamps for clips to enable proper display of clip origin.

Revision ID: 003
Revises: 002_add_media_tables
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '003_add_clip_timestamps'
down_revision = '002_add_media_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add start_time and end_time columns to clips table.
    
    These columns store ABSOLUTE timestamps in the source media,
    not relative timestamps. This allows proper display of where
    in the source media a clip originates from.
    
    Nullable for backwards compatibility with existing clips.
    """
    op.add_column('clips', sa.Column('start_time', sa.Float(), nullable=True))
    op.add_column('clips', sa.Column('end_time', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove start_time and end_time columns from clips table."""
    op.drop_column('clips', 'end_time')
    op.drop_column('clips', 'start_time')
