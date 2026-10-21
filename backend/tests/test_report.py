from pathlib import Path
from tests.test_api import populate
from tests.test_valuation import TARGET

def test_pdf_api_and_cyrillic(client,auth,db):
    headers=auth();populate(db)
    v=client.post('/api/v1/valuations',headers=headers,json=TARGET).json()
    response=client.get(f"/api/v1/valuations/{v['id']}/report",headers=headers)
    assert response.status_code==200
    assert response.headers['content-type']=='application/pdf'
    assert response.content.startswith(b'%PDF-')
    assert len(response.content)>10000
    output=Path('../tmp/pdfs')
    output.mkdir(parents=True,exist_ok=True)
    (output/'sample-report.pdf').write_bytes(response.content)
