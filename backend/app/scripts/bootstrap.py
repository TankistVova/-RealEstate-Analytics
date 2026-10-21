import os
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import User
from app.core.security import ph
from app.services.settings import get_settings

def main():
    with SessionLocal() as db:
        get_settings(db)
        email=os.getenv('ADMIN_EMAIL','').strip().lower()
        password=os.getenv('ADMIN_PASSWORD','')
        if email and password:
            if len(password)<12: raise ValueError('ADMIN_PASSWORD: минимум 12 символов')
            user=db.scalar(select(User).where(User.email==email))
            if user is None:
                db.add(User(email=email,password_hash=ph.hash(password),role='admin'))
                db.commit()

if __name__=='__main__': main()
