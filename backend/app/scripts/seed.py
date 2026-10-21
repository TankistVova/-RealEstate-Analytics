from datetime import date, timedelta
import random
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import Property

def main():
    rng=random.Random(42)
    added=0
    with SessionLocal() as db:
        existing=set(db.scalars(select(Property.external_id).where(Property.source_name=='Синтетические демонстрационные данные')))
        for i in range(90):
            external=f'demo-{i:03d}'
            if external in existing: continue
            district=['Центр','Западный','Северный'][i%3]
            rooms=1+(i//3)%3
            area=round(rooms*20+15+rng.uniform(-6,6),1)
            floors=rng.choice([5,9,16,20])
            db.add(Property(city='Ростов-на-Дону',district=district,address=f'Демонстрационная улица, {i+1}',rooms=rooms,total_area=area,floor=rng.randint(1,floors),floors_total=floors,year_built=rng.randint(1970,2023),building_type=rng.choice(['panel','brick','monolith']),condition=rng.choice(['needs_repair','normal','good','excellent']),price_rub=round(area*rng.uniform(85000,135000)/1000)*1000,listing_date=date.today()-timedelta(days=rng.randint(0,120)),latitude=47.235+ rng.uniform(-.04,.04),longitude=39.70+rng.uniform(-.08,.06),source_name='Синтетические демонстрационные данные',external_id=external,status='active'))
            added+=1
        db.commit()
    print(f'Добавлено синтетических объектов: {added}')

if __name__=='__main__': main()
