"""add razorpay billing fields

Revision ID: adc4be973f46
Revises: 9c156934069a
Create Date: 2026-11-17 16:59:02.876583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adc4be973f46'
down_revision: Union[str, Sequence[str], None] = '9c156934069a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
