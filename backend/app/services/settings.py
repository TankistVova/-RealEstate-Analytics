from app.models.entities import ValuationSettings
from app.schemas.inputs import Coefficients, ComparisonRules

def get_settings(db):
    settings = db.get(ValuationSettings, 1)
    if settings is None:
        settings = ValuationSettings(id=1, coefficients=Coefficients().model_dump(), comparison_rules=ComparisonRules().model_dump())
        db.add(settings)
        db.commit()
    return settings
