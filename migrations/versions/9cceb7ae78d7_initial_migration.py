"""Initial migration.

Revision ID: 9cceb7ae78d7
Revises: 
Create Date: 2024-10-06 13:52:05.945249

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9cceb7ae78d7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('vendors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cafe_name', sa.String(length=255), nullable=False),
    sa.Column('owner_name', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('address_type', sa.String(length=50), nullable=True),
    sa.Column('address_line1', sa.String(length=255), nullable=True),
    sa.Column('address_line2', sa.String(length=255), nullable=True),
    sa.Column('pincode', sa.String(length=20), nullable=True),
    sa.Column('state', sa.String(length=100), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('latitude', sa.String(length=50), nullable=True),
    sa.Column('longitude', sa.String(length=50), nullable=True),
    sa.Column('registration_number', sa.String(length=100), nullable=True),
    sa.Column('registration_date', sa.Date(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('famous_game_list', sa.String(length=255), nullable=True),
    sa.Column('amenities', sa.JSON(), nullable=True),
    sa.Column('opening_time', sa.Time(), nullable=True),
    sa.Column('closing_time', sa.Time(), nullable=True),
    sa.Column('opening_days', sa.JSON(), nullable=True),
    sa.Column('available_games', sa.JSON(), nullable=True),
    sa.Column('credential_username', sa.String(length=150), nullable=True),
    sa.Column('credential_password', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('credential_username')
    )
    op.create_table('documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('vendor_id', sa.Integer(), nullable=False),
    sa.Column('document_type', sa.String(length=100), nullable=False),
    sa.Column('file_path', sa.String(length=255), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('documents')
    op.drop_table('vendors')
    # ### end Alembic commands ###
