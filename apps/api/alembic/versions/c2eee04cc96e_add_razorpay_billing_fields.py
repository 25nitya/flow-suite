
"""add razorpay billing fields

Revision ID: c2eee04cc96e
Revises: adc4be973f46
"""

from alembic import op
import sqlalchemy as sa


revision = "c2eee04cc96e"
down_revision = "adc4be973f46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Organizations: Razorpay customer reference
    op.add_column(
        "organizations",
        sa.Column("razorpay_customer_id", sa.String(120), nullable=True),
    )

    # Plans: Razorpay plan reference and pricing
    op.add_column(
        "plans",
        sa.Column("razorpay_plan_id", sa.String(120), nullable=True),
    )
    op.add_column(
        "plans",
        sa.Column("amount_paise", sa.Integer(), nullable=True),
    )
    op.add_column(
        "plans",
        sa.Column("currency", sa.String(3), nullable=True),
    )
    op.add_column(
        "plans",
        sa.Column("billing_interval", sa.String(20), nullable=True),
    )

    # Subscriptions: Razorpay subscription reference
    op.add_column(
        "subscriptions",
        sa.Column("razorpay_subscription_id", sa.String(120), nullable=True),
    )

    # Populate pricing for existing plans
    op.execute("""
        UPDATE plans
        SET amount_paise = CASE
            WHEN slug = 'free' THEN 0
            WHEN slug = 'pro' THEN 49900
            WHEN slug = 'business' THEN 149900
            ELSE 0
        END,
        currency = 'INR',
        billing_interval = 'monthly'
    """)

    # Make pricing fields mandatory after backfilling
    op.alter_column(
        "plans",
        "amount_paise",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "plans",
        "currency",
        existing_type=sa.String(3),
        nullable=False,
    )
    op.alter_column(
        "plans",
        "billing_interval",
        existing_type=sa.String(20),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "razorpay_subscription_id")

    op.drop_column("plans", "billing_interval")
    op.drop_column("plans", "currency")
    op.drop_column("plans", "amount_paise")
    op.drop_column("plans", "razorpay_plan_id")

    op.drop_column("organizations", "razorpay_customer_id")
