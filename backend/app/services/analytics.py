from statistics import mean, median
from collections import defaultdict

def summarize(records):
    if not records:
        return {'count':0, 'average_per_m2':None, 'median_per_m2':None, 'districts':[], 'distribution':[], 'area_prices':[], 'rooms':[], 'history':[], 'synthetic_count':0}
    ppm=[p['price_rub']/p['total_area'] for p in records]
    groups=defaultdict(list)
    room_groups=defaultdict(list)
    history=defaultdict(list)
    for p in records:
        groups[(p['city'],p['district'])].append(p['price_rub']/p['total_area'])
        room_groups[p['rooms']].append(p['price_rub'])
        history[str(p['listing_date'])[:7]].append(p['price_rub']/p['total_area'])
    lo=min(p['price_rub'] for p in records)
    hi=max(p['price_rub'] for p in records)
    width=max((hi-lo)/8, 1)
    distribution=[{'label':f'{(lo+i*width)/1e6:.1f}–{(lo+(i+1)*width)/1e6:.1f}', 'count':0} for i in range(8)]
    for p in records:
        distribution[min(7,int((p['price_rub']-lo)/width))]['count']+=1
    periods=[{'month':k,'median':median(v),'count':len(v)} for k,v in sorted(history.items()) if len(v)>=3]
    return dict(count=len(records), average_per_m2=mean(ppm), median_per_m2=median(ppm), synthetic_count=sum(p.get('source_name')=='Синтетические демонстрационные данные' for p in records), districts=[{'city':c,'district':d,'median':median(v),'count':len(v)} for (c,d),v in sorted(groups.items())], distribution=distribution, area_prices=[{'area':p['total_area'],'price':p['price_rub'],'id':p['id']} for p in records], rooms=[{'rooms':k,'average':mean(v),'median':median(v),'count':len(v)} for k,v in sorted(room_groups.items())], history=periods if len(periods)>=3 else [])
