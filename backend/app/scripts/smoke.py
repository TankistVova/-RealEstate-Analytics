"""Exercise a running local API against seeded synthetic data; no credentials are printed."""
import secrets
import httpx

def main():
    credentials={'email':f'smoke-{secrets.token_hex(6)}@example.com','password':secrets.token_urlsafe(24)}
    target=dict(city='Ростов-на-Дону',district='Центр',address=None,total_area=55,rooms=2,floor=5,floors_total=9,year_built=None,building_type='brick',condition='good')
    with httpx.Client(base_url='http://127.0.0.1:8000/api/v1',timeout=30) as client:
        registration=client.post('/auth/register',json=credentials)
        registration.raise_for_status()
        login=client.post('/auth/login',json=credentials); login.raise_for_status()
        client.headers['Authorization']='Bearer '+login.json()['access_token']
        assert client.get('/auth/me').json()['role']=='user'
        overview=client.get('/analytics/overview');overview.raise_for_status()
        assert overview.json()['synthetic_count']>=60, 'Сначала выполните app.scripts.seed'
        response=client.post('/valuations',json=target);response.raise_for_status()
        valuation=response.json(); id=valuation['id']
        assert len(valuation['result_data']['analogs'])>=3
        assert abs(sum(a['weight'] for a in valuation['result_data']['analogs'])-1)<1e-10
        assert any('синтетические' in warning.lower() for warning in valuation['result_data']['warnings'])
        assert client.get(f'/valuations/{id}').json()['result_data']==valuation['result_data']
        assert client.get('/valuations').json()['total']>=1
        pdf=client.get(f'/valuations/{id}/report');pdf.raise_for_status()
        assert pdf.content.startswith(b'%PDF-')
        for section in ['districts','price-distribution','area-prices','price-history','rooms']:
            client.get('/analytics/'+section).raise_for_status()
        objects=client.get('/properties?page_size=200');objects.raise_for_status()
        assert any(p['latitude'] is not None for p in objects.json()['items'])
        assert client.get('/admin/settings').status_code==403
        assert client.delete(f'/valuations/{id}').status_code==204
        assert client.get(f'/valuations/{id}').status_code==404
        print('API smoke passed: registration, login, seeded valuation, snapshots, history, PDF, analytics, map data, permissions, deletion.')

if __name__=='__main__':main()
