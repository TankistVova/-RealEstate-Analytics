from datetime import date,timedelta
import pytest
from app.schemas.inputs import Apartment,PropertyInput,Coefficients,ComparisonRules
from app.services.valuation import calculate
from app.services.comparables import similarity,select_comparables,floor_category

TARGET=dict(city='Ростов-на-Дону',district='Центр',address=None,total_area=60,rooms=2,floor=5,floors_total=9,year_built=None,building_type='panel',condition='normal')
COEFFICIENTS=Coefficients().model_dump()
RULES=ComparisonRules().model_dump()

def record(id=1,**kw):
    return {**TARGET,'id':id,'price_rub':6000000,'listing_date':str(date.today()),'status':'active','source_name':None,**kw}

def test_price_and_weights_and_rounding():
    r=calculate(TARGET,[record(i) for i in range(1,4)],COEFFICIENTS,RULES)
    assert r['estimated_price']==6000000
    assert r['price_per_m2']==pytest.approx(100000)
    assert sum(a['weight'] for a in r['analogs'])==pytest.approx(1)
    assert r['min_price']==5400000
    assert r['max_price']==6600000

def test_corrections_are_ratios_and_clamped():
    target={**TARGET,'condition':'excellent','building_type':'monolith'}
    r=calculate(target,[record(i,condition='needs_repair',floor=1) for i in range(3)],COEFFICIENTS,RULES)
    a=r['analogs'][0]
    assert a['corrections']['condition']==pytest.approx(1.12/.9)
    assert a['corrections']['building']==pytest.approx(1.05)
    assert a['corrections']['floor']==pytest.approx(1/.96)
    assert a['total_correction']==1.25
    assert a['correction_limited']

def test_weighted_mean_matches_manual():
    r=calculate(TARGET,[record(1),record(2,total_area=65,price_rub=7200000),record(3,floor=1,price_rub=5500000)],COEFFICIENTS,RULES)
    expected=sum(a['corrected_price_per_m2']*a['similarity']**2 for a in r['analogs'])/sum(a['similarity']**2 for a in r['analogs'])
    assert r['price_per_m2']==pytest.approx(expected)
    assert r['estimated_price']%1000==0

@pytest.mark.parametrize('stage,overrides',[(1,{}),(2,{'district':'Северный'}),(3,{'district':'Западный','rooms':3})])
def test_search_expands(stage,overrides):
    chosen,warnings,_,actual=select_comparables(TARGET,[record(i,**overrides) for i in range(3)],RULES)
    assert len(chosen)==3 and actual==stage
    assert bool(warnings)==(stage>1)

def test_stale_inactive_other_city_and_invalid_excluded():
    data=[record(i) for i in range(3)]+[record(4,listing_date=str(date.today()-timedelta(days=181))),record(5,status='inactive'),record(6,city='Москва'),record(7,total_area=0)]
    chosen,_,diagnostics,_=select_comparables(TARGET,data,RULES)
    assert {p['id'] for p in chosen}=={0,1,2}
    assert len(diagnostics)==4

def test_tie_break_is_date_not_price():
    data=[record(i,price_rub=6000000+i*1000,listing_date=str(date.today()-timedelta(days=i))) for i in range(12)]
    chosen,*_=select_comparables(TARGET,data,RULES)
    assert [p['id'] for p in chosen]==list(range(10))

def test_insufficient_and_iqr_diagnostics():
    with pytest.raises(ValueError,match='Недостаточно'): calculate(TARGET,[record(1),record(2)],COEFFICIENTS,RULES)
    data=[record(i,price_rub=6000000+i*10000) for i in range(6)]+[record(99,price_rub=100000000)]
    r=calculate(TARGET,data,COEFFICIENTS,RULES)
    assert 99 not in [p['id'] for p in r['analogs']]
    assert any(d['reason']=='Ценовой выброс IQR' for d in r['diagnostics'])

def test_similarity_formula_and_floor():
    assert similarity(TARGET,record())==pytest.approx(1)
    assert floor_category(record(floor=1,floors_total=1))=='first'
    assert similarity(TARGET,record(total_area=81,district='other',rooms=3,floor=1))==pytest.approx(.1+.075+.06)

@pytest.mark.parametrize('changes',[{'total_area':0},{'floor':10},{'rooms':0},{'city':''},{'total_area':float('nan')},{'building_type':'unknown'}])
def test_validation(changes):
    with pytest.raises(ValueError): Apartment.model_validate({**TARGET,**changes})

def test_settings_validation():
    with pytest.raises(ValueError): Coefficients(condition={'normal':0})
    with pytest.raises(ValueError): ComparisonRules(area_tolerances=[.35,.25,.3])
