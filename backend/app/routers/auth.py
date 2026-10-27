from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    user = User(
        full_name=body.full_name.strip(),
        email=str(body.email).lower(),
        password_hash=hash_password(body.password),
        phone=body.phone,
        role="user",
        status="active",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email address is already registered",
        )
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(body.email).lower()).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not currently permitted to sign in. Please contact the administrator.",
        )
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout():
    return {"message": "Signed out. Delete the token on the client."}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user