"""create phone number for user column

Revision ID: 8a1eb92b8ac9
Revises: 
Create Date: 2025-07-15 15:03:20.054371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a1eb92b8ac9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True))

    pass


def downgrade() -> None:
    op.drop_column('users', 'phone_number')


