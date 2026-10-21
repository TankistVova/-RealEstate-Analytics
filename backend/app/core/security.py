import os
import secrets
from pathlib import Path
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import User

ph = PasswordHasher()
bearer = HTTPBearer(auto_error=False)

def secret():
    configured = os.getenv('JWT_SECRET')
    if configured:
        if len(configured) < 32:
            raise RuntimeError('JWT_SECRET должен содержать минимум 32 символа')
        return configured
    path = Path(os.getenv('JWT_SECRET_FILE', '/state/jwt-secret' if Path('/state').exists() else '.jwt-secret'))
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48), encoding='utf-8')
    return path.read_text(encoding='utf-8').strip()

def token(user):
    return jwt.encode({'sub': str(user.id), 'exp': datetime.now(timezone.utc)+timedelta(hours=8)}, secret(), algorithm='HS256')

def verify(password, hashed):
    try:
        return ph.verify(hashed, password)
    except VerificationError:
        return False

def current_user(auth: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    try:
        claims = jwt.decode(auth.credentials if auth else '', secret(), algorithms=['HS256'])
        user = db.get(User, int(claims['sub']))
        if user is None:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, 'Необходима авторизация')

def admin(user=Depends(current_user)):
    if user.role != 'admin':
        raise HTTPException(403, 'Доступно только администратору')
    return user
