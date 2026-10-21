from decimal import Decimal, ROUND_HALF_UP
from math import prod
from app.services.comparables import floor_category, similarity, select_comparables

def calculate(target, records, coefficients, rules):
    selected, warnings, diagnostics, stage = select_comparables(target, records, rules)
    similarities = [similarity(target, p) for p in selected]
    denominator = sum(s*s for s in similarities)
    analogs=[]
    for p, score in zip(selected, similarities):
        corrections = {name: coefficients[table][target[field]]/coefficients[table][p[field]] for name, table, field in [('condition','condition','condition'),('building','building','building_type')]}
        corrections['floor'] = coefficients['floor'][floor_category(target)]/coefficients['floor'][floor_category(p)]
        raw = prod(corrections.values())
        multiplier = max(coefficients['correction_min'], min(coefficients['correction_max'], raw))
        original = p['price_rub']/p['total_area']
        analogs.append({**p, 'similarity':score, 'weight':score*score/denominator, 'price_per_m2':original, 'corrections':corrections, 'raw_correction':raw, 'total_correction':multiplier, 'correction_limited':raw!=multiplier, 'corrected_price_per_m2':original*multiplier})
    ppm=sum(p['corrected_price_per_m2']*p['weight'] for p in analogs)
    total=float((Decimal(str(ppm*target['total_area']))/1000).quantize(Decimal('1'), rounding=ROUND_HALF_UP)*1000)
    if any(p.get('source_name')=='Синтетические демонстрационные данные' for p in analogs):
        warnings.append('В расчёте использованы синтетические демонстрационные данные. Результат не отражает текущий рынок.')
    return dict(estimated_price=total, price_per_m2=ppm, min_price=round(total*(1-coefficients['range_percent']),2), max_price=round(total*(1+coefficients['range_percent']),2), analogs=analogs, warnings=warnings, diagnostics=diagnostics, search_stage=stage, method='Сравнительный подход; веса пропорциональны квадрату схожести', range_note='Условный ориентировочный диапазон, не статистический доверительный интервал')
