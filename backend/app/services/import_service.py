from io import BytesIO
import pandas as pd
from sqlalchemy import select
from app.schemas.inputs import PropertyInput
from app.models.entities import Property

ALIASES = dict(zip(['Город','Район','Адрес','Комнаты','Площадь','Этаж','Этажность','Год постройки','Тип дома','Состояние','Цена','Дата объявления','Широта','Долгота'], ['city','district','address','rooms','total_area','floor','floors_total','year_built','building_type','condition','price_rub','listing_date','latitude','longitude']))
VALUES={'Панельный':'panel','Кирпичный':'brick','Монолитный':'monolith','Другой':'other','Требует ремонта':'needs_repair','Обычное':'normal','Хорошее':'good','Отличное':'excellent'}

def fingerprint(p):
    return tuple(str(p.get(k) or '').strip().casefold() for k in ['city','district','address','rooms','total_area','floor','floors_total','price_rub','listing_date'])

def import_data(db, content, filename, preview=False):
    stream=BytesIO(content)
    if filename.lower().endswith('.csv'):
        frame=pd.read_csv(stream, encoding='utf-8-sig', sep=None, engine='python')
    elif filename.lower().endswith('.xlsx'):
        frame=pd.read_excel(stream, engine='openpyxl')
    else:
        raise ValueError('Поддерживаются только CSV и XLSX')
    if len(frame)>20000:
        raise ValueError('Максимум 20 000 строк в одном файле')
    frame=frame.rename(columns=lambda c:ALIASES.get(str(c).strip(),str(c).strip()))
    required={'city','district','rooms','total_area','floor','floors_total','building_type','condition','price_rub','listing_date'}
    if not required.issubset(frame.columns):
        raise ValueError('Отсутствуют колонки: '+', '.join(sorted(required-set(frame.columns))))
    existing=[{c.name:getattr(p,c.name) for c in Property.__table__.columns} for p in db.scalars(select(Property))]
    seen={fingerprint(p) for p in existing}
    external={(p['source_name'],p['external_id']) for p in existing if p['external_id']}
    result={'total':len(frame),'imported':0,'duplicates':0,'errors':[],'preview':preview}
    for index,row in frame.iterrows():
        try:
            raw={k:(None if pd.isna(v) else v) for k,v in row.to_dict().items() if k in PropertyInput.model_fields}
            for key in ['building_type','condition']:
                raw[key]=VALUES.get(raw.get(key),raw.get(key))
            for key in ['total_area','price_rub','kitchen_area','latitude','longitude']:
                if isinstance(raw.get(key),str): raw[key]=raw[key].replace(' ','').replace(',','.')
            if isinstance(raw.get('listing_date'),pd.Timestamp): raw['listing_date']=raw['listing_date'].date()
            p=PropertyInput.model_validate(raw).model_dump()
            key=fingerprint(p)
            ext=(p['source_name'],p['external_id'])
            if key in seen or (p['external_id'] and ext in external):
                result['duplicates']+=1
                continue
            seen.add(key)
            if p['external_id']: external.add(ext)
            if not preview: db.add(Property(**p))
            result['imported']+=1
        except (ValueError,TypeError) as error:
            result['errors'].append({'row':int(index)+2,'message':str(error)})
    if not preview: db.commit()
    return result
