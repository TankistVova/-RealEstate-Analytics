import os
os.environ['JWT_SECRET']='test-only-secret-with-more-than-32-characters'
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.session import Base, get_db
from app.main import app
from app.models.entities import User

@pytest.fixture
def db():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(engine,expire_on_commit=False)() as session:
        yield session
    engine.dispose()

@pytest.fixture
def client(db):
    app.dependency_overrides[get_db]=lambda:db
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear()

@pytest.fixture
def auth(client,db):
    def register(email='user@example.com',admin=False):
        response=client.post('/api/v1/auth/register',json={'email':email,'password':'test-password-123'})
        assert response.status_code==201,response.text
        if admin:
            user=db.get(User,response.json()['user']['id']);user.role='admin';db.commit()
        return {'Authorization':'Bearer '+response.json()['access_token']}
    return register
