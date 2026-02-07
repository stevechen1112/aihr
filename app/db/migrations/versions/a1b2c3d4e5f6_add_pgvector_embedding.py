"""add pgvector embedding column to documentchunks

Revision ID: a1b2c3d4e5f6
Revises: eb7fe95812e8
Create Date: 2026-02-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'eb7fe95812e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # 2. Add embedding column (1024 dimensions for voyage-4-lite)
    #    Use raw SQL since Alembic doesn't natively support vector type
    op.execute('ALTER TABLE documentchunks ADD COLUMN IF NOT EXISTS embedding vector(1024)')

    # 3. Create HNSW index for fast cosine similarity search
    op.execute('''
        CREATE INDEX IF NOT EXISTS ix_documentchunks_embedding_cosine
        ON documentchunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    ''')

    # 4. Create composite index for tenant-scoped vector search
    op.create_index(
        'ix_documentchunks_tenant_embedding',
        'documentchunks',
        ['tenant_id'],
        postgresql_where=sa.text('embedding IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_documentchunks_tenant_embedding', table_name='documentchunks')
    op.execute('DROP INDEX IF EXISTS ix_documentchunks_embedding_cosine')
    op.drop_column('documentchunks', 'embedding')
