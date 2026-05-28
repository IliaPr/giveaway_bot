"""restore participant profile fields

Revision ID: e1834f6b2d10
Revises: 43829d9b672e
Create Date: 2026-05-27 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1834f6b2d10"
down_revision: Union[str, Sequence[str], None] = "43829d9b672e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("participants", sa.Column(
        "full_name", sa.String(length=255), nullable=True))
    op.add_column("participants", sa.Column(
        "phone", sa.String(length=64), nullable=True))
    op.add_column("participants", sa.Column(
        "company", sa.String(length=255), nullable=True))
    op.add_column("participants", sa.Column(
        "position", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("participants", "position")
    op.drop_column("participants", "company")
    op.drop_column("participants", "phone")
    op.drop_column("participants", "full_name")
