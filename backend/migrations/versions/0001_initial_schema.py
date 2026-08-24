"""Initial schema for the ticket booking system."""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("CUSTOMER", "ORGANISER", "ADMIN", name="userrole", native_enum=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "venues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "venue_seats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("venue_id", sa.Integer(), sa.ForeignKey("venues.id"), nullable=False),
        sa.Column("row_label", sa.String(length=16), nullable=False),
        sa.Column("seat_number", sa.Integer(), nullable=False),
        sa.Column("category", sa.Enum("PREMIUM", "STANDARD", name="seatcategory", native_enum=False), nullable=False),
        sa.Column("x_position", sa.Integer(), nullable=False),
        sa.Column("y_position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("venue_id", "row_label", "seat_number", name="uq_venue_seat"),
    )
    op.create_index("ix_venue_seats_venue_id", "venue_seats", ["venue_id"], unique=False)

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organiser_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("venue_id", sa.Integer(), sa.ForeignKey("venues.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Enum("MOVIE", "CONCERT", name="eventtype", native_enum=False), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("status", sa.Enum("PUBLISHED", "CANCELLED", name="eventstatus", native_enum=False), nullable=False),
        sa.Column("standard_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("premium_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_events_organiser_id", "events", ["organiser_id"], unique=False)
    op.create_index("ix_events_venue_id", "events", ["venue_id"], unique=False)
    op.create_index("ix_events_event_date", "events", ["event_date"], unique=False)

    op.create_table(
        "seat_holds",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Enum("ACTIVE", "COMPLETED", "EXPIRED", "RELEASED", name="holdstatus", native_enum=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_seat_holds_user_id", "seat_holds", ["user_id"], unique=False)
    op.create_index("ix_seat_holds_event_id", "seat_holds", ["event_id"], unique=False)
    op.create_index("ix_seat_holds_expires_at", "seat_holds", ["expires_at"], unique=False)

    op.create_table(
        "event_seats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("venue_seat_id", sa.Integer(), sa.ForeignKey("venue_seats.id"), nullable=False),
        sa.Column("category", sa.Enum("PREMIUM", "STANDARD", name="eventseatcategory", native_enum=False), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.Enum("AVAILABLE", "HELD", "BOOKED", name="eventseatstatus", native_enum=False), nullable=False),
        sa.Column("hold_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hold_id", sa.String(length=36), sa.ForeignKey("seat_holds.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("event_id", "venue_seat_id", name="uq_event_venue_seat"),
    )
    op.create_index("ix_event_seats_event_id", "event_seats", ["event_id"], unique=False)
    op.create_index("ix_event_seats_status", "event_seats", ["status"], unique=False)
    op.create_index("ix_event_seats_hold_expires_at", "event_seats", ["hold_expires_at"], unique=False)
    op.create_index("ix_event_seats_hold_id", "event_seats", ["hold_id"], unique=False)

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_reference", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.Enum("CONFIRMED", "CANCELLED", name="bookingstatus", native_enum=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("booking_reference"),
    )
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"], unique=False)
    op.create_index("ix_bookings_event_id", "bookings", ["event_id"], unique=False)
    op.create_index("ix_bookings_booking_reference", "bookings", ["booking_reference"], unique=False)

    op.create_table(
        "booking_seats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("event_seat_id", sa.Integer(), sa.ForeignKey("event_seats.id"), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.UniqueConstraint("booking_id", "event_seat_id", name="uq_booking_event_seat"),
    )

    op.create_table(
        "waitlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category", sa.Enum("PREMIUM", "STANDARD", name="waitlistcategory", native_enum=False), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("WAITING", "OFFERED", "COMPLETED", "REMOVED", name="waitliststatus", native_enum=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_waitlist_event_id", "waitlist", ["event_id"], unique=False)
    op.create_index("ix_waitlist_category", "waitlist", ["category"], unique=False)
    op.create_index("ix_waitlist_status", "waitlist", ["status"], unique=False)
    op.create_index(
        "uq_waitlist_active",
        "waitlist",
        ["event_id", "user_id", "category"],
        unique=True,
        postgresql_where=sa.text("status IN ('WAITING', 'OFFERED')"),
    )

    op.create_table(
        "waitlist_offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("waitlist_id", sa.Integer(), sa.ForeignKey("waitlist.id"), nullable=False),
        sa.Column("event_seat_id", sa.Integer(), sa.ForeignKey("event_seats.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "ACCEPTED", "EXPIRED", "CANCELLED", name="waitlistofferstatus", native_enum=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_waitlist_offers_expires_at", "waitlist_offers", ["expires_at"], unique=False)
    op.create_index("ix_waitlist_offers_status", "waitlist_offers", ["status"], unique=False)
    op.create_index(
        "uq_waitlist_offer_pending_seat",
        "waitlist_offers",
        ["event_seat_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    op.drop_index("uq_waitlist_offer_pending_seat", table_name="waitlist_offers", postgresql_where=sa.text("status = 'PENDING'"))
    op.drop_index("ix_waitlist_offers_status", table_name="waitlist_offers")
    op.drop_index("ix_waitlist_offers_expires_at", table_name="waitlist_offers")
    op.drop_table("waitlist_offers")

    op.drop_index("uq_waitlist_active", table_name="waitlist", postgresql_where=sa.text("status IN ('WAITING', 'OFFERED')"))
    op.drop_index("ix_waitlist_status", table_name="waitlist")
    op.drop_index("ix_waitlist_category", table_name="waitlist")
    op.drop_index("ix_waitlist_event_id", table_name="waitlist")
    op.drop_table("waitlist")

    op.drop_table("booking_seats")

    op.drop_index("ix_bookings_booking_reference", table_name="bookings")
    op.drop_index("ix_bookings_event_id", table_name="bookings")
    op.drop_index("ix_bookings_user_id", table_name="bookings")
    op.drop_table("bookings")

    op.drop_index("ix_event_seats_hold_id", table_name="event_seats")
    op.drop_index("ix_event_seats_hold_expires_at", table_name="event_seats")
    op.drop_index("ix_event_seats_status", table_name="event_seats")
    op.drop_index("ix_event_seats_event_id", table_name="event_seats")
    op.drop_table("event_seats")

    op.drop_index("ix_seat_holds_expires_at", table_name="seat_holds")
    op.drop_index("ix_seat_holds_event_id", table_name="seat_holds")
    op.drop_index("ix_seat_holds_user_id", table_name="seat_holds")
    op.drop_table("seat_holds")

    op.drop_index("ix_events_event_date", table_name="events")
    op.drop_index("ix_events_venue_id", table_name="events")
    op.drop_index("ix_events_organiser_id", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_venue_seats_venue_id", table_name="venue_seats")
    op.drop_table("venue_seats")

    op.drop_table("venues")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

