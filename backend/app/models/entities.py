from datetime import datetime, date, timezone
from sqlalchemy import String, Float, Integer, DateTime, Date, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

def now():
    return datetime.now(timezone.utc)

json_type = JSON().with_variant(JSONB, 'postgresql')

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(20), default='user')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Property(Base):
    __tablename__ = 'properties'
    id: Mapped[int] = mapped_column(primary_key=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    district: Mapped[str] = mapped_column(String(120), index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    rooms: Mapped[int] = mapped_column(Integer, index=True)
    total_area: Mapped[float] = mapped_column(Float)
    kitchen_area: Mapped[float | None] = mapped_column(Float)
    floor: Mapped[int] = mapped_column(Integer)
    floors_total: Mapped[int] = mapped_column(Integer)
    year_built: Mapped[int | None] = mapped_column(Integer)
    building_type: Mapped[str] = mapped_column(String(30))
    condition: Mapped[str] = mapped_column(String(30))
    price_rub: Mapped[float] = mapped_column(Float, index=True)
    listing_date: Mapped[date] = mapped_column(Date, index=True)
    source_name: Mapped[str | None] = mapped_column(String(150))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    external_id: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(20), default='active')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class Valuation(Base):
    __tablename__ = 'valuations'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    input_parameters: Mapped[dict] = mapped_column(json_type)
    estimated_price: Mapped[float] = mapped_column(Float)
    price_per_m2: Mapped[float] = mapped_column(Float)
    min_price: Mapped[float] = mapped_column(Float)
    max_price: Mapped[float] = mapped_column(Float)
    result_data: Mapped[dict] = mapped_column(json_type)
    coefficients_snapshot: Mapped[dict] = mapped_column(json_type)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class ValuationSettings(Base):
    __tablename__ = 'valuation_settings'
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    settings_version: Mapped[int] = mapped_column(default=1)
    coefficients: Mapped[dict] = mapped_column(json_type)
    comparison_rules: Mapped[dict] = mapped_column(json_type)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
