"""Preserve migration history after the initial schema migration."""

from typing import Sequence, Union

revision: str = "8c21c793ec6f"
down_revision: Union[str, Sequence[str], None] = "c2eee04cc96e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
