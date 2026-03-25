"""add_route_geometry_to_rides

Revision ID: a15b9070ee62
Revises: 7b8e1f2a3d4c
Create Date: 2026-03-24 15:30:43.752821

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision = "a15b9070ee62"
down_revision = "7b8e1f2a3d4c"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("rides", sa.Column("route_geometry", geoalchemy2.types.Geography(geometry_type="LINESTRING", srid=4326, from_text="ST_GeogFromText", name="geography"), nullable=True))
    op.create_index("idx_rides_route_geometry", "rides", ["route_geometry"], unique=False, postgresql_using="gist")

def downgrade() -> None:
    op.drop_index("idx_rides_route_geometry", table_name="rides", postgresql_using="gist")
    op.drop_column("rides", "route_geometry")
