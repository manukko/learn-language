from datetime import timedelta
import datetime
from typing import Any, Callable
import uuid
import env
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.db.models import User, SessionLocal
from src.db.redis import token_in_blocklist
from itsdangerous import URLSafeTimedSerializer

# Secret key and JWT settings: to define in env.py
SECRET_KEY = env.SECRET_KEY
ALGORITHM = env.ALGORITHM

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={
        "error": "Could not validate credentials"
    },
    headers={"WWW-Authenticate": "Bearer"},
)

TOKEN_IN_BLOCKLIST_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={
        "error": "Could not validate credentials: Your token is invalid or has been revoked",
        "resolution": "Please get a valid token"
    },
    headers={"WWW-Authenticate": "Bearer"},
)

INVALID_TOKEN_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={
        "error": "Could not validate credentials: Your token is invalid or expired",
        "resolution": "Please get a valid token"
    },
    headers={"WWW-Authenticate": "Bearer"},
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

salt = "email-configuration"
serializer = URLSafeTimedSerializer(
    secret_key=env.SECRET_KEY,
    salt=salt
)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_token(
    data: dict,
    expires_delta: timedelta,
    is_refresh_token: bool = False
):
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    to_encode.update({"refresh": is_refresh_token})
    to_encode.update({"jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if user and verify_password(password, user.hashed_password):
        return user
    return None


def validate_token(token: str, is_refresh_token: bool = False) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        refresh = payload.get("refresh")
        exp = payload.get("exp")
        jti = payload.get("jti")
        if (
            username is None
            or exp is None
            or refresh is None
            or refresh != is_refresh_token
            or datetime.datetime.fromtimestamp(exp) < datetime.datetime.now()
        ):
            raise INVALID_TOKEN_EXCEPTION
        if token_in_blocklist(jti):
            raise TOKEN_IN_BLOCKLIST_EXCEPTION
    except JWTError:
        raise INVALID_TOKEN_EXCEPTION
    return payload


def get_current_user_factory(
    is_refresh_token: bool = False
) -> Callable[[], User]:
    def get_current_user_closure(    
            token: str = Depends(oauth2_scheme), 
            db: Session = Depends(get_db_session)
        ):
        payload = validate_token(token, is_refresh_token)
        username = payload.get("sub")
        user = get_user(db, username)
        if user is None:
            raise CREDENTIALS_EXCEPTION 
        return user
    return get_current_user_closure

def validate_token_factory(
    is_refresh_token: bool = False
) -> Callable[[], dict[str, Any]]:
    def validate_token_closure(    
            token: str = Depends(oauth2_scheme)
        ):
        payload = validate_token(token, is_refresh_token)
        return payload
    return validate_token_closure


def create_url_safe_token(data: dict):
    token = serializer.dumps(data)
    return token

def decode_url_safe_token(token: str) -> dict:
    try:
        data = serializer.loads(token)
        return data
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None
    