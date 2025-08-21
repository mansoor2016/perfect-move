"""Add NLP search suggestion tables only

Revision ID: fae3d815c9b6
Revises: 2b00395aa7d8
Create Date: 2025-08-22 00:31:36.430305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fae3d815c9b6'
down_revision: Union[str, None] = '2b00395aa7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create search suggestion patterns table
    op.create_table('search_suggestion_patterns',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('text', sa.String(length=500), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True, default=0),
        sa.Column('success_rate', sa.Float(), nullable=True, default=0.0),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('priority', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for search suggestion patterns
    op.create_index('idx_search_suggestions_category', 'search_suggestion_patterns', ['category'], unique=False)
    op.create_index('idx_search_suggestions_active', 'search_suggestion_patterns', ['is_active'], unique=False)
    op.create_index('idx_search_suggestions_priority', 'search_suggestion_patterns', ['priority'], unique=False)
    op.create_index('idx_search_suggestions_text', 'search_suggestion_patterns', ['text'], unique=False)
    
    # Create search query logs table
    op.create_table('search_query_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('parsed_entities', sa.JSON(), nullable=True),
        sa.Column('search_criteria', sa.JSON(), nullable=True),
        sa.Column('results_count', sa.Integer(), nullable=True),
        sa.Column('user_clicked_result', sa.Boolean(), nullable=True, default=False),
        sa.Column('user_saved_search', sa.Boolean(), nullable=True, default=False),
        sa.Column('parse_time_ms', sa.Integer(), nullable=True),
        sa.Column('search_time_ms', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for search query logs
    op.create_index('idx_search_logs_created_at', 'search_query_logs', ['created_at'], unique=False)
    op.create_index('idx_search_logs_user_id', 'search_query_logs', ['user_id'], unique=False)
    op.create_index('idx_search_logs_session_id', 'search_query_logs', ['session_id'], unique=False)


def downgrade() -> None:
    # Drop search query logs table and indexes
    op.drop_index('idx_search_logs_session_id', table_name='search_query_logs')
    op.drop_index('idx_search_logs_user_id', table_name='search_query_logs')
    op.drop_index('idx_search_logs_created_at', table_name='search_query_logs')
    op.drop_table('search_query_logs')
    
    # Drop search suggestion patterns table and indexes
    op.drop_index('idx_search_suggestions_text', table_name='search_suggestion_patterns')
    op.drop_index('idx_search_suggestions_priority', table_name='search_suggestion_patterns')
    op.drop_index('idx_search_suggestions_active', table_name='search_suggestion_patterns')
    op.drop_index('idx_search_suggestions_category', table_name='search_suggestion_patterns')
    op.drop_table('search_suggestion_patterns')