"""
app/routers/auth.py

Authentication endpoints:
  POST /register — create a new member account (public)
  POST /login    — return a JWT access token
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import User, UserRole
from app.schemas import MessageResponse, RegisterResponse, TokenResponse, UserLoginRequest, UserPublicResponse, UserRegisterRequest

router = APIRouter(tags=["Auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new club member",
)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> dict:
    """
    Create a new account with role=member.
    Returns user data **and** a JWT so the client is immediately authenticated.
    """
    # Guard against duplicate emails
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.member,
        chesscom_username=payload.chesscom_username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create a JWT immediately so the client doesn't need a second /login call
    token = create_access_token({"sub": user.email, "role": user.role.value})

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "chesscom_username": user.chesscom_username,
        "blitz_rating": user.blitz_rating,
        "rapid_rating": user.rapid_rating,
        "created_at": user.created_at,
        "access_token": token,
        "token_type": "bearer",
    }


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive a JWT",
)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> dict:
    """
    Verify email + password, return a signed JWT.
    The token encodes the user's email in the 'sub' claim and role.
    """
    user: User | None = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.email, "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}
