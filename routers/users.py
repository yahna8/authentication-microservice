from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta
from database import get_db
from models import User
import os

load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET")

router = APIRouter()


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class TokenData(BaseModel):
    user_id: int


def create_access_token(user_id: int):
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Extract user from token
def get_current_user(
    authorization: str = Header(None), db: Session = Depends(get_db)
):
    """
    Decode JWT and return authenticated user.
    """
    if authorization is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    # Remove "Bearer " prefix if present
    token = authorization.replace("Bearer ", "").strip()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Registration endpoint
@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    hashed_password = bcrypt.hash(user.password)
    db_user = User(name=user.name, email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered successfully"}


# Login endpoint
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not bcrypt.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user_id=db_user.id)
    return {"access_token": token, "token_type": "bearer"}


# Token validation endpoint
@router.get("/validate")
def validate_token(token: str, x_internal_secret: str = Header(None)):
    # Validate internal secret
    if x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": user_id}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/profile")
def get_profile(user: User = Depends(get_current_user)):
    """
    Retrieve authenticated user's profile (name & email).
    """
    return {"name": user.name, "email": user.email}
