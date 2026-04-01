"""add_community_ride_verification

Revision ID: c1b7d4e5f6a7
Revises: a15b9070ee62
Create Date: 2026-04-01 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c1b7d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a15b9070ee62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.execute("ALTER TYPE ridestatus RENAME TO ridestatus_old")
    new_ride_status = postgresql.ENUM(
        "SCHEDULED",
        "STARTED",
        "COMPLETED",
        "CANCELLED",
        "MISSED_START",
        name="ridestatus",
    )
    new_ride_status.create(bind, checkfirst=False)

    op.execute("ALTER TABLE rides ALTER COLUMN status DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE rides
        ALTER COLUMN status TYPE ridestatus
        USING (
            CASE status::text
                WHEN 'ACTIVE' THEN 'SCHEDULED'
                WHEN 'COMPLETED' THEN 'COMPLETED'
                WHEN 'CANCELLED' THEN 'CANCELLED'
                ELSE 'SCHEDULED'
            END
        )::ridestatus
        """
    )
    op.execute("ALTER TABLE rides ALTER COLUMN status SET DEFAULT 'SCHEDULED'")
    op.execute("DROP TYPE ridestatus_old")

    ride_completion_source = postgresql.ENUM("DRIVER", "SYSTEM", name="ridecompletionsource")
    booking_trip_status = postgresql.ENUM(
        "BOOKED",
        "READY_AT_PICKUP",
        "BOARDED",
        "DROPPED",
        "NO_SHOW",
        name="bookingtripstatus",
    )
    ride_completion_source.create(bind, checkfirst=True)
    booking_trip_status.create(bind, checkfirst=True)

    op.add_column("rides", sa.Column("actual_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rides", sa.Column("actual_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rides", sa.Column("actual_start_lat", sa.Float(), nullable=True))
    op.add_column("rides", sa.Column("actual_start_lng", sa.Float(), nullable=True))
    op.add_column("rides", sa.Column("actual_complete_lat", sa.Float(), nullable=True))
    op.add_column("rides", sa.Column("actual_complete_lng", sa.Float(), nullable=True))
    op.add_column(
        "rides",
        sa.Column("completed_by", sa.Enum("DRIVER", "SYSTEM", name="ridecompletionsource"), nullable=True),
    )

    op.add_column(
        "bookings",
        sa.Column(
            "trip_status",
            sa.Enum(
                "BOOKED",
                "READY_AT_PICKUP",
                "BOARDED",
                "DROPPED",
                "NO_SHOW",
                name="bookingtripstatus",
            ),
            nullable=False,
            server_default="BOOKED",
        ),
    )
    op.add_column("bookings", sa.Column("boarded_seats", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bookings", sa.Column("passenger_ready_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("boarded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("passenger_boarding_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("settled_amount_paise", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bookings", sa.Column("refunded_amount_paise", sa.Integer(), nullable=False, server_default="0"))

    op.execute(
        """
        UPDATE bookings AS b
        SET trip_status = 'DROPPED'::bookingtripstatus,
            boarded_seats = b.seats_booked,
            settled_amount_paise = b.seats_booked * COALESCE(r.price_per_seat, 0) * 100
        FROM rides AS r
        WHERE r.id = b.ride_id
          AND b.status = 'CONFIRMED'
        """
    )

    op.drop_index("unique_active_ride_passenger", table_name="bookings")
    op.create_index(
        "unique_active_ride_passenger",
        "bookings",
        ["ride_id", "passenger_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING_PAYMENT', 'PAID_HELD', 'CONFIRMED')"),
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("unique_active_ride_passenger", table_name="bookings")
    op.create_index(
        "unique_active_ride_passenger",
        "bookings",
        ["ride_id", "passenger_id"],
        unique=True,
        postgresql_where=sa.text("((status)::text = 'CONFIRMED'::text)"),
    )

    op.drop_column("bookings", "refunded_amount_paise")
    op.drop_column("bookings", "settled_amount_paise")
    op.drop_column("bookings", "passenger_boarding_confirmed_at")
    op.drop_column("bookings", "boarded_at")
    op.drop_column("bookings", "passenger_ready_at")
    op.drop_column("bookings", "boarded_seats")
    op.drop_column("bookings", "trip_status")
    op.drop_column("rides", "completed_by")
    op.drop_column("rides", "actual_complete_lng")
    op.drop_column("rides", "actual_complete_lat")
    op.drop_column("rides", "actual_start_lng")
    op.drop_column("rides", "actual_start_lat")
    op.drop_column("rides", "actual_completed_at")
    op.drop_column("rides", "actual_started_at")

    op.execute("ALTER TYPE ridestatus RENAME TO ridestatus_new")
    old_ride_status = postgresql.ENUM("ACTIVE", "COMPLETED", "CANCELLED", name="ridestatus")
    old_ride_status.create(bind, checkfirst=False)
    op.execute("ALTER TABLE rides ALTER COLUMN status DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE rides
        ALTER COLUMN status TYPE ridestatus
        USING (
            CASE status::text
                WHEN 'SCHEDULED' THEN 'ACTIVE'
                WHEN 'STARTED' THEN 'ACTIVE'
                WHEN 'MISSED_START' THEN 'CANCELLED'
                WHEN 'COMPLETED' THEN 'COMPLETED'
                WHEN 'CANCELLED' THEN 'CANCELLED'
                ELSE 'ACTIVE'
            END
        )::ridestatus
        """
    )
    op.execute("ALTER TABLE rides ALTER COLUMN status SET DEFAULT 'ACTIVE'")
    op.execute("DROP TYPE ridestatus_new")

    op.execute("DROP TYPE bookingtripstatus")
    op.execute("DROP TYPE ridecompletionsource")
