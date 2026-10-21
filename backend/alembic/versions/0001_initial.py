"""Initial application schema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0001'
down_revision = None

def upgrade():
    json = sa.JSON().with_variant(JSONB, 'postgresql')
    op.create_table('users', sa.Column('id',sa.Integer,primary_key=True),sa.Column('email',sa.String(254),nullable=False,unique=True),sa.Column('password_hash',sa.String(512),nullable=False),sa.Column('role',sa.String(20),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    columns=[sa.Column('id',sa.Integer,primary_key=True)]
    for name,size in [('city',120),('district',120),('address',500),('building_type',30),('condition',30),('source_name',150),('source_url',1000),('external_id',150),('status',20)]:
        columns.append(sa.Column(name,sa.String(size),nullable=name in {'address','source_name','source_url','external_id'}))
    for name in ['rooms','floor','floors_total','year_built']:
        columns.append(sa.Column(name,sa.Integer,nullable=name=='year_built'))
    for name in ['total_area','price_rub','latitude','longitude','kitchen_area']:
        columns.append(sa.Column(name,sa.Float,nullable=name not in {'total_area','price_rub'}))
    columns += [sa.Column('listing_date',sa.Date,nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False)]
    op.create_table('properties',*columns)
    for name in ['city','district','rooms','price_rub','listing_date']:
        op.create_index('ix_properties_'+name,'properties',[name])
    op.create_table('valuations',sa.Column('id',sa.Integer,primary_key=True),sa.Column('user_id',sa.Integer,sa.ForeignKey('users.id'),nullable=False),*[sa.Column(n,json,nullable=False) for n in ['input_parameters','result_data','coefficients_snapshot']],*[sa.Column(n,sa.Float,nullable=False) for n in ['estimated_price','price_per_m2','min_price','max_price']],sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_valuations_user_id','valuations',['user_id'])
    op.create_table('valuation_settings',sa.Column('id',sa.Integer,primary_key=True),sa.Column('settings_version',sa.Integer,nullable=False),sa.Column('coefficients',json,nullable=False),sa.Column('comparison_rules',json,nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():
    for table in ['valuation_settings','valuations','properties','users']:
        op.drop_table(table)
