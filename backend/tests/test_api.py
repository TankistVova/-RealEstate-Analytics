from datetime import date
from io import BytesIO
import pandas as pd
import pytest
from app.models.entities import Property
from app.services.import_service import import_data
from app.schemas.inputs import PropertyInput
from tests.test_valuation import TARGET,record

def populate(db):
    for i in range(6):
        p=PropertyInput.model_validate({k:v for k,v in record(i).items() if k!='id'})
        db.add(Property(**p.model_dump()))
    db.commit()

def test_auth_and_admin_permissions(client,auth):
    assert client.get('/api/v1/properties').status_code==401
    headers=auth()
    assert client.get('/api/v1/auth/me',headers=headers).json()['role']=='user'
    assert client.get('/api/v1/admin/settings',headers=headers).status_code==403
    assert client.post('/api/v1/properties',headers=headers,json={}).status_code==403
    assert client.post('/api/v1/auth/register',json={'email':'user@example.com','password':'password1234'}).status_code==409
    assert client.post('/api/v1/auth/login',json={'email':'user@example.com','password':'wrong-password'}).status_code==401
    assert client.post('/api/v1/auth/login',json={'email':'user@example.com','password':'test-password-123'}).status_code==200

def test_snapshot_and_owner_isolation(client,auth,db):
    first=auth('first@example.com'); second=auth('second@example.com'); administrator=auth('admin@example.com',True)
    populate(db)
    result=client.post('/api/v1/valuations',headers=first,json=TARGET)
    assert result.status_code==201,result.text
    original=result.json(); id=original['id']
    assert len(original['result_data']['analogs'])==6
    assert client.get(f'/api/v1/valuations/{id}',headers=second).status_code==404
    assert client.delete(f'/api/v1/valuations/{id}',headers=second).status_code==404
    assert client.get(f'/api/v1/valuations/{id}/report',headers=second).status_code==404
    assert client.get('/api/v1/valuations',headers=second).json()['total']==0
    settings=client.get('/api/v1/admin/settings',headers=administrator).json()
    settings['coefficients']['condition']['normal']=1.2
    assert client.patch('/api/v1/admin/settings',headers=administrator,json={k:settings[k] for k in ['coefficients','comparison_rules']}).status_code==200
    assert client.patch('/api/v1/properties/1',headers=administrator,json={'price_rub':9999999}).status_code==200
    assert client.get(f'/api/v1/valuations/{id}',headers=first).json()==original
    assert client.get('/api/v1/analytics/overview',headers=first).json()['valuation_count']==1

def test_property_crud_filters_and_validation(client,auth):
    headers=auth(admin=True)
    p=PropertyInput.model_validate({k:v for k,v in record().items() if k!='id'}).model_dump(mode='json')
    created=client.post('/api/v1/properties',headers=headers,json=p)
    assert created.status_code==201,created.text
    id=created.json()['id']
    assert client.patch(f'/api/v1/properties/{id}',headers=headers,json={'floor':100}).status_code==422
    assert client.get('/api/v1/properties?rooms=3',headers=headers).json()['total']==0
    assert client.get('/api/v1/properties?page=0',headers=headers).status_code==422
    assert client.get('/api/v1/properties?city=Ростов-на-Дону',headers=headers).json()['total']==1
    assert client.get('/api/v1/analytics/overview',headers=headers).json()['median_per_m2']==100000
    assert client.delete(f'/api/v1/properties/{id}',headers=headers).status_code==204
    assert client.get(f'/api/v1/properties/{id}',headers=headers).status_code==404

@pytest.mark.parametrize('extension',['csv','xlsx'])
def test_import_validation_duplicates_preview(db,extension):
    valid=PropertyInput.model_validate({k:v for k,v in record().items() if k!='id'}).model_dump(mode='json')
    frame=pd.DataFrame([valid,{**valid,'price_rub':-10},valid])
    stream=BytesIO()
    if extension=='csv': content=frame.to_csv(index=False).encode('utf-8-sig')
    else: frame.to_excel(stream,index=False);content=stream.getvalue()
    preview=import_data(db,content,'input.'+extension,True)
    assert preview['imported']==1 and preview['duplicates']==1 and len(preview['errors'])==1
    assert db.query(Property).count()==0
    result=import_data(db,content,'input.'+extension)
    assert result['imported']==1 and db.query(Property).count()==1
    assert import_data(db,content,'input.'+extension)['duplicates']==2

def test_import_api_russian_columns_and_size(client,auth):
    h=auth(admin=True)
    text=f'Город;Район;Комнаты;Площадь;Этаж;Этажность;Тип дома;Состояние;Цена;Дата объявления\nРостов-на-Дону;Центр;2;60;5;9;Кирпичный;Хорошее;6000000;{date.today()}\n'
    response=client.post('/api/v1/admin/import?preview=false',headers=h,files={'file':('data.csv',text.encode('utf-8-sig'),'text/csv')})
    assert response.status_code==200,response.text
    assert response.json()['imported']==1
    assert client.post('/api/v1/admin/import',headers=h,files={'file':('bad.csv',b'foo\nbar','text/csv')}).status_code==422
    assert client.post('/api/v1/admin/import',headers=h,files={'file':('huge.csv',b'x'*(10*1024*1024+1),'text/csv')}).status_code==413

def test_insufficient_api(client,auth):
    headers=auth()
    assert client.post('/api/v1/valuations',headers=headers,json=TARGET).status_code==422
