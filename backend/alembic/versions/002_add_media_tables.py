"""Add media, transcriptions, highlights, clips tables

Revision ID: 002_add_media_tables
Revises: 001_initial
Create Date: 2025-01-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_media_tables'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create media table
    op.create_table(
        'media',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('original_filename', sa.String(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('thumbnail_path', sa.String(), nullable=True),
        sa.Column('media_type', sa.String(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_media_project_id', 'media', ['project_id'])
    
    # Create transcriptions table
    op.create_table(
        'transcriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('media_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('language', sa.String(), nullable=False, server_default='en'),
        sa.Column('full_text', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['media_id'], ['media.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_transcriptions_media_id', 'transcriptions', ['media_id'])
    op.create_unique_constraint('uq_transcriptions_media_id', 'transcriptions', ['media_id'])
    
    # Create transcript_segments table
    op.create_table(
        'transcript_segments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('transcription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('segment_index', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('speaker', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.ForeignKeyConstraint(['transcription_id'], ['transcriptions.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_transcript_segments_transcription_id', 'transcript_segments', ['transcription_id'])
    
    # Create highlights table
    op.create_table(
        'highlights',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('media_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('highlight_id', sa.String(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('transcript_segment_ids', postgresql.ARRAY(sa.Integer()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['media_id'], ['media.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_highlights_media_id', 'highlights', ['media_id'])
    
    # Create clips table
    op.create_table(
        'clips',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('media_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('has_captions', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['media_id'], ['media.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_clips_media_id', 'clips', ['media_id'])


def downgrade() -> None:
    op.drop_index('idx_clips_media_id', table_name='clips')
    op.drop_table('clips')
    
    op.drop_index('idx_highlights_media_id', table_name='highlights')
    op.drop_table('highlights')
    
    op.drop_index('idx_transcript_segments_transcription_id', table_name='transcript_segments')
    op.drop_table('transcript_segments')
    
    op.drop_constraint('uq_transcriptions_media_id', 'transcriptions', type_='unique')
    op.drop_index('idx_transcriptions_media_id', table_name='transcriptions')
    op.drop_table('transcriptions')
    
    op.drop_index('idx_media_project_id', table_name='media')
    op.drop_table('media')


