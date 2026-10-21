from datetime import date, timedelta
from statistics import quantiles

def floor_category(p):
    return 'first' if p['floor'] == 1 else 'last' if p['floor'] == p['floors_total'] else 'middle'

def similarity(target, analog):
    area = max(0, 1-abs(target['total_area']-analog['total_area'])/(.35*target['total_area']))
    rooms = abs(target['rooms']-analog['rooms'])
    return .5*area + .25*(1 if target['district']==analog['district'] else .4) + .15*(1 if rooms==0 else .5 if rooms==1 else 0) + .1*(1 if floor_category(target)==floor_category(analog) else .6)

def select_comparables(target, records, rules):
    diagnostics = []
    eligible = []
    cutoff = date.today()-timedelta(days=rules['max_age_days'])
    for p in records:
        dt = date.fromisoformat(str(p['listing_date'])[:10])
        reason = None
        if p['status'] != 'active': reason = 'Неактивное объявление'
        elif not cutoff <= dt <= date.today(): reason = 'Неактуальная дата'
        elif p['total_area'] <= 0 or p['price_rub'] <= 0 or not 1 <= p['floor'] <= p['floors_total']: reason = 'Некорректные параметры'
        elif p['city'] != target['city']: reason = 'Другой город'
        if reason:
            diagnostics.append({'id':p['id'], 'reason':reason})
        else:
            eligible.append(p)
    warnings = []
    for stage, tolerance in enumerate(rules['area_tolerances']):
        chosen = [p for p in eligible if abs(p['total_area']-target['total_area'])/target['total_area'] <= tolerance and abs(p['rooms']-target['rooms']) <= (1 if stage==2 else 0) and (stage>0 or p['district']==target['district'])]
        if len(chosen)>=5:
            values = [p['price_rub']/p['total_area'] for p in chosen]
            q1, _, q3 = quantiles(values, n=4, method='inclusive')
            iqr = q3-q1
            if iqr>0:
                retained=[]
                for p in chosen:
                    if q1-1.5*iqr <= p['price_rub']/p['total_area'] <= q3+1.5*iqr:
                        retained.append(p)
                    else:
                        diagnostics.append({'id':p['id'], 'reason':'Ценовой выброс IQR', 'stage':stage+1})
                chosen=retained
        if len(chosen)>=3:
            if stage:
                warnings.append(f'Условия поиска расширены до этапа {stage+1}: район может отличаться' + (', число комнат ±1' if stage==2 else ''))
            chosen.sort(key=lambda p:(similarity(target,p), str(p['listing_date']), -p['id']), reverse=True)
            return chosen[:rules['max_comparables']], warnings, diagnostics, stage+1
    raise ValueError('Недостаточно данных для надёжной оценки: требуется минимум три аналога')
