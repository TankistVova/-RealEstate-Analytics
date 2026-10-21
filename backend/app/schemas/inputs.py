from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict, model_validator

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class Apartment(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)
    city: str = Field(min_length=1, max_length=120)
    district: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=500)
    total_area: float = Field(gt=0, le=1000)
    rooms: int = Field(ge=1, le=20)
    floor: int = Field(ge=1, le=200)
    floors_total: int = Field(ge=1, le=200)
    year_built: int | None = Field(default=None, ge=1800, le=date.today().year)
    building_type: Literal['panel', 'brick', 'monolith', 'other']
    condition: Literal['needs_repair', 'normal', 'good', 'excellent']

    @model_validator(mode='after')
    def check_floor(self):
        if self.floor > self.floors_total:
            raise ValueError('Этаж не может превышать этажность здания')
        return self

class PropertyInput(Apartment):
    price_rub: float = Field(gt=0, le=1e12)
    listing_date: date
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    kitchen_area: float | None = Field(default=None, gt=0)
    source_name: str | None = Field(default=None, max_length=150)
    source_url: str | None = Field(default=None, max_length=1000)
    external_id: str | None = Field(default=None, max_length=150)
    status: Literal['active', 'inactive'] = 'active'

    @model_validator(mode='after')
    def check_property(self):
        if self.listing_date > date.today():
            raise ValueError('Дата объявления не может быть в будущем')
        if self.kitchen_area and self.kitchen_area > self.total_area:
            raise ValueError('Площадь кухни превышает общую площадь')
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('Укажите обе координаты')
        return self

class Coefficients(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    condition: dict[str, float] = Field(default_factory=lambda: dict(needs_repair=.9, normal=1, good=1.06, excellent=1.12))
    building: dict[str, float] = Field(default_factory=lambda: dict(panel=1, brick=1.03, monolith=1.05, other=1))
    floor: dict[str, float] = Field(default_factory=lambda: dict(first=.96, last=.97, middle=1))
    correction_min: float = Field(default=.8, ge=.5, le=1)
    correction_max: float = Field(default=1.25, ge=1, le=2)
    range_percent: float = Field(default=.1, gt=0, le=.5)

    @model_validator(mode='after')
    def check_maps(self):
        for name, keys in [('condition', {'needs_repair','normal','good','excellent'}), ('building', {'panel','brick','monolith','other'}), ('floor', {'first','last','middle'})]:
            values = getattr(self, name)
            if set(values) != keys or any(not .5 <= x <= 2 for x in values.values()):
                raise ValueError('Некорректные коэффициенты: ' + name)
        return self

class ComparisonRules(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    area_tolerances: list[float] = Field(default_factory=lambda: [.25,.30,.35], min_length=3, max_length=3)
    max_age_days: int = Field(default=180, ge=1, le=730)
    max_comparables: int = Field(default=10, ge=3, le=10)

    @model_validator(mode='after')
    def check_tolerances(self):
        if any(not 0 < v <= .75 for v in self.area_tolerances) or self.area_tolerances != sorted(self.area_tolerances):
            raise ValueError('Диапазоны площади должны возрастать и быть в пределах (0; 0.75]')
        return self

class SettingsInput(BaseModel):
    coefficients: Coefficients
    comparison_rules: ComparisonRules
