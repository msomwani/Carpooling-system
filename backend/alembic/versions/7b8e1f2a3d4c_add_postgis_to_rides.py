"""add postgis columns to rides

Revision ID: 7b8e1f2a3d4c
Revises: 6782d29d9789
Create Date: 2026-03-24 13:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography

# revision identifiers, used by Alembic.
revision: str = '7b8e1f2a3d4c'
down_revision: Union[str, Sequence[str], None] = '6782d29d9789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enable PostGIS extension
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    
    # Add geography columns
    op.add_column('rides', sa.Column('source_location', Geography(geometry_type='POINT', srid=4326, spatial_index=True), nullable=True))
    op.add_column('rides', sa.Column('destination_location', Geography(geometry_type='POINT', srid=4326, spatial_index=True), nullable=True))
    
    # Security note: this SQL is safe from injection because:
    # - All identifiers (source_lng, source_lat, etc.) are hardcoded column names, not user input.
    # - There are no string interpolations or f-strings with external values.
    # - The WHERE clause also only references static column names.
    op.execute('''
        UPDATE rides 
        SET source_location = ST_SetSRID(ST_MakePoint(source_lng, source_lat), 4326)::geography,
            destination_location = ST_SetSRID(ST_MakePoint(destination_lng, destination_lat), 4326)::geography
        WHERE source_lat IS NOT NULL AND source_lng IS NOT NULL;
    ''')

def downgrade() -> None:
    op.drop_column('rides', 'destination_location')
    op.drop_column('rides', 'source_location')
