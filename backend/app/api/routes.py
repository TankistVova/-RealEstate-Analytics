from datetime import date, timedelta, datetime, timezone
from io import BytesIO
import zipfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import User, Property, Valuation
from app.schemas.inputs import Credentials, Apartment, PropertyInput, SettingsInput
from app.core.security import ph, token, verify, current_user, admin
from app.services.settings import get_settings
from app.services.valuation import calculate
from app.services.analytics import summarize
from app.services.import_service import import_data
from app.services.pdf_service import report

router=APIRouter(prefix='/api/v1')

def serialize(obj):
    values={c.name:getattr(obj,c.name) for c in obj.__table__.columns}
    for key,value in values.items():
        if isinstance(value,datetime) and value.tzinfo is None:
            values[key]=value.replace(tzinfo=timezone.utc)
    return jsonable_encoder(values)

def user_info(user): return dict(id=user.id,email=user.email,role=user.role)

@router.post('/auth/register',status_code=201)
def register(body:Credentials, db:Session=Depends(get_db)):
    user=User(email=str(body.email).lower(),password_hash=ph.hash(body.password),role='user')
    db.add(user)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Этот email уже зарегистрирован')
    return {'access_token':token(user),'token_type':'bearer','user':user_info(user)}

@router.post('/auth/login')
def login(body:Credentials,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==str(body.email).lower()))
    if not user or not verify(body.password,user.password_hash):
        raise HTTPException(401,'Неверный email или пароль')
    return {'access_token':token(user),'token_type':'bearer','user':user_info(user)}

@router.get('/auth/me')
def me(user=Depends(current_user)): return user_info(user)

def filtered(city:str|None=None,district:str|None=None,rooms:int|None=Query(None,ge=1),area_min:float|None=Query(None,gt=0),area_max:float|None=Query(None,gt=0),date_from:date|None=None,date_to:date|None=None,q:str|None=None,status:str|None=None):
    statement=select(Property)
    for field,value in [('city',city),('district',district),('rooms',rooms),('status',status)]:
        if value is not None: statement=statement.where(getattr(Property,field)==value)
    if area_min is not None: statement=statement.where(Property.total_area>=area_min)
    if area_max is not None: statement=statement.where(Property.total_area<=area_max)
    if date_from: statement=statement.where(Property.listing_date>=date_from)
    if date_to: statement=statement.where(Property.listing_date<=date_to)
    if q: statement=statement.where(or_(Property.address.ilike('%'+q+'%'),Property.district.ilike('%'+q+'%'),Property.city.ilike('%'+q+'%')))
    return statement

@router.get('/properties')
def properties(statement=Depends(filtered),page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=200),db:Session=Depends(get_db),user=Depends(current_user)):
    total=db.scalar(select(func.count()).select_from(statement.subquery()))
    return {'items':[serialize(p) for p in db.scalars(statement.order_by(Property.id.desc()).offset((page-1)*page_size).limit(page_size))],'total':total,'page':page,'page_size':page_size}

@router.get('/properties/meta')
def metadata(db:Session=Depends(get_db),user=Depends(current_user)):
    return {'locations':[dict(city=c,district=d) for c,d in db.execute(select(Property.city,Property.district).distinct().order_by(Property.city,Property.district))]}

def property_or_404(db,id):
    p=db.get(Property,id)
    if p is None: raise HTTPException(404,'Объект не найден')
    return p

@router.get('/properties/{id}')
def property_detail(id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    return serialize(property_or_404(db,id))

@router.post('/properties',status_code=201)
def add_property(body:PropertyInput,db:Session=Depends(get_db),user=Depends(admin)):
    p=Property(**body.model_dump()); db.add(p); db.commit()
    return serialize(p)

@router.patch('/properties/{id}')
def edit_property(id:int,body:dict,db:Session=Depends(get_db),user=Depends(admin)):
    p=property_or_404(db,id)
    old={k:getattr(p,k) for k in PropertyInput.model_fields}
    try: validated=PropertyInput.model_validate({**old,**body})
    except ValueError as e: raise HTTPException(422,str(e))
    for k,v in validated.model_dump().items(): setattr(p,k,v)
    db.commit()
    return serialize(p)

@router.delete('/properties/{id}',status_code=204)
def delete_property(id:int,db:Session=Depends(get_db),user=Depends(admin)):
    db.delete(property_or_404(db,id)); db.commit()

@router.post('/valuations',status_code=201)
def create_valuation(body:Apartment,db:Session=Depends(get_db),user=Depends(current_user)):
    settings=get_settings(db)
    records=[serialize(p) for p in db.scalars(select(Property).where(Property.city==body.city))]
    try: result=calculate(body.model_dump(),records,settings.coefficients,settings.comparison_rules)
    except ValueError as e: raise HTTPException(422, str(e))
    valuation=Valuation(user_id=user.id,input_parameters=body.model_dump(),result_data=result,coefficients_snapshot={'version':settings.settings_version,'coefficients':settings.coefficients,'comparison_rules':settings.comparison_rules},**{k:result[k] for k in ['estimated_price','price_per_m2','min_price','max_price']})
    db.add(valuation); db.commit()
    return serialize(valuation)

@router.get('/valuations')
def valuations(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),user=Depends(current_user)):
    statement=select(Valuation).where(Valuation.user_id==user.id)
    return dict(items=[serialize(v) for v in db.scalars(statement.order_by(Valuation.id.desc()).offset((page-1)*page_size).limit(page_size))],total=db.scalar(select(func.count()).select_from(statement.subquery())))

def owned(db,id,user):
    v=db.scalar(select(Valuation).where(Valuation.id==id,Valuation.user_id==user.id))
    if v is None: raise HTTPException(404,'Оценка не найдена')
    return v

@router.get('/valuations/{id}')
def valuation_detail(id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    return serialize(owned(db,id,user))

@router.delete('/valuations/{id}',status_code=204)
def valuation_delete(id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    db.delete(owned(db,id,user)); db.commit()

@router.get('/valuations/{id}/report')
def valuation_report(id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    return Response(report(owned(db,id,user)),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="valuation-{id}.pdf"'})

@router.get('/analytics/{section}')
def analytics(section:str,statement=Depends(filtered),db:Session=Depends(get_db),user=Depends(current_user)):
    records=[serialize(p) for p in db.scalars(statement.where(Property.status=='active'))]
    result=summarize(records)
    if section=='overview':
        result['total_count']=db.scalar(select(func.count()).select_from(statement.subquery()))
        cutoff=date.today()-timedelta(days=get_settings(db).comparison_rules['max_age_days'])
        result['comparable_count']=sum(cutoff<=date.fromisoformat(p['listing_date'])<=date.today() for p in records)
        result['valuation_count']=db.scalar(select(func.count()).select_from(Valuation).where(Valuation.user_id==user.id))
        return result
    keys={'districts':'districts','price-distribution':'distribution','area-prices':'area_prices','price-history':'history','rooms':'rooms'}
    if section not in keys: raise HTTPException(404,'Раздел не найден')
    return result[keys[section]]

@router.get('/admin/settings')
def settings_read(db:Session=Depends(get_db),user=Depends(admin)):
    return serialize(get_settings(db))

@router.patch('/admin/settings')
def settings_write(body:SettingsInput,db:Session=Depends(get_db),user=Depends(admin)):
    s=get_settings(db)
    s.coefficients=body.coefficients.model_dump(); s.comparison_rules=body.comparison_rules.model_dump(); s.settings_version+=1
    db.commit()
    return serialize(s)

@router.post('/admin/import')
async def import_file(file:UploadFile=File(...),preview:bool=True,db:Session=Depends(get_db),user=Depends(admin)):
    content=await file.read(10*1024*1024+1)
    if len(content)>10*1024*1024: raise HTTPException(413,'Максимальный размер файла 10 МБ')
    try:
        if (file.filename or '').lower().endswith('.xlsx'):
            with zipfile.ZipFile(BytesIO(content)) as z:
                if sum(i.file_size for i in z.infolist())>60*1024*1024: raise ValueError('Распакованный XLSX превышает 60 МБ')
        return import_data(db,content,file.filename or '',preview)
    except Exception as e:
        db.rollback()
        raise HTTPException(422,'Не удалось обработать файл: '+str(e))
