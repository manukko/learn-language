import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.db.models import User
from src.auth.auth import (
    get_db_session,
    get_current_user_factory,
    get_user_by_email,
    create_token,
    authenticate_user,
    get_password_hash,
    validate_token_factory,
    create_url_safe_token,
    decode_url_safe_token
)
from fastapi.security import OAuth2PasswordRequestForm
from src.db.redis import add_jti_to_blocklist
from src.schemas.users import ResetPasswordModel, SendResetPasswordLinkModel, UserCreate, UserModel
from src.mail import mail, create_message
import env
router = APIRouter()

DOMAIN = env.DOMAIN

USERNAME_FORBIDDEN_CHARACTERS = list("$%\\/<>:^?!")
ACCESS_TOKEN_DEFAULT_LIFESPAN_MINUTES = 180
REFRESH_TOKEN_DEFAULT_LIFESPAN_HOURS = 168


def check_username(username: str) -> bool:
    return (
        len(username) >= 5
        and len(username) <= 30
        and not any(c in USERNAME_FORBIDDEN_CHARACTERS for c in username)
    )


def check_password(password: str) -> bool:
    return (
        len(password) >= 9
        and len(password) <= 30
        and any(c.isdigit() for c in password)
        and any(c.isalpha() for c in password)
    )


# User registration
@router.post("/register")
async def register(user: UserCreate, backgroud_tasks: BackgroundTasks, db: Session = Depends(get_db_session)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already registered"
        )
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    if not check_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Username must contain 5 to 30 characters, not in the list {USERNAME_FORBIDDEN_CHARACTERS}",
        )
    if not check_password(user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password must contain 9 to 30 characters, including at least one letter and one digit",
        )
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password, email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Send email for user verification
    token = create_url_safe_token({"email": user.email})
    link_to_verify_email = f"http://{DOMAIN}/api/v1/users/verify/{token}"
    html_message = f"""
    link = 
    <h1>Verify your email</h1>
    <p>Click this link <a href="{link_to_verify_email}">link</a> to verify your email address:</p>
    """

    message = create_message(
        recipients=[user.email],
        subject="Verify your email",
        body=html_message
    )
    backgroud_tasks.add_task(mail.send_message, message)

    return {
        "message": "User created successfully. Check your email to verify your account.",
        "user": new_user
    }

@router.get("/verify/{token}")
async def verify_user_account(
    token: str,
    db : Session = Depends(get_db_session)
):
    try:
        token_data = decode_url_safe_token(token)
        user_email = token_data.get("email")
    except Exception:
        raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Sorry, an unexpected error has occurred while decoding verification token...",
            )

    if user_email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )        
    user = get_user_by_email(db, user_email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return JSONResponse (
        status_code=status.HTTP_200_OK,
        content={
            "message": "User verified successfully!"
        }
    )


# User authentication: return a bearer token that allows the user to access the service
@router.post("/get_access_token")
def get_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db_session),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_token(
        data={"sub": user.username, "email": user.email},
        expires_delta=datetime.timedelta(minutes=ACCESS_TOKEN_DEFAULT_LIFESPAN_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}

# User authentication: return a bearer token that allows the user to access the service
@router.post("/get_refresh_token")
def get_refresh_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db_session),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    refresh_token = create_token(
        data={"sub": user.username},
        expires_delta=datetime.timedelta(hours=REFRESH_TOKEN_DEFAULT_LIFESPAN_HOURS),
        is_refresh_token=True
    )
    return {"refresh_token": refresh_token, "token_type": "bearer"}

@router.get("/refresh_access_token")
def get_refresh_token_from_access_token(
    current_user: User = Depends(get_current_user_factory(is_refresh_token=True)),
):
    access_token = create_token(
        data={"sub": current_user.username},
        expires_delta=datetime.timedelta(minutes=ACCESS_TOKEN_DEFAULT_LIFESPAN_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"} 

@router.get("/logout")
def revoke_token(token_details: dict[str, Any] = Depends(validate_token_factory())):
    print(token_details)
    jti = token_details.get("jti")
    print(jti)
    add_jti_to_blocklist(jti)
    return JSONResponse  (
        status_code=status.HTTP_200_OK,
        content={
            "message": "Logged out successfully"
        }
    )

@router.delete("/delete")
def delete_user(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_factory()),
):
    db.delete(current_user)
    db.commit()
    return {"message": "User deleted"}

@router.get("/me", response_model=UserModel)
def get_current_user(current_user = Depends(get_current_user_factory())):
    return current_user

@router.post("/send_reset_password_link")
def send_reset_password_link(
    password_reset_model: SendResetPasswordLinkModel,
    backgroud_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    
    if get_user_by_email(db, password_reset_model.email) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User for email {password_reset_model.email} does not exist.",
        )

    # Send email for password reset
    token = create_url_safe_token({"email": password_reset_model.email})
    link_to_reset_password = f"http://{DOMAIN}/api/v1/users/reset_password/{token}"
    html_message = f"""
    link = 
    <h1>Verify your email</h1>
    <p>Click this link <a href="{link_to_reset_password}">link</a> to reset your password:</p>
    """

    message = create_message(
        recipients=[password_reset_model.email],
        subject="Reset password",
        body=html_message
    )
    backgroud_tasks.add_task(mail.send_message, message)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content="Please check the provided email to reset your password"
    )

@router.post("/reset_password/{token}")
def reset_password(
    token: str,
    reset_password_model: ResetPasswordModel,
    db: Session = Depends(get_db_session)
):
    
    if not check_password(reset_password_model.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password must contain 9 to 30 characters, including at least one letter and one digit",
        )
    if reset_password_model.password != reset_password_model.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password and password confirmation must match",
        )
    
    try:
        token_data: dict = decode_url_safe_token(token)
        user_email = token_data.get("email")
    except Exception:
        raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Sorry, an unexpected error has occurred while decoding verification token...",
            )
    
    user = get_user_by_email(db, user_email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.hashed_password = get_password_hash(reset_password_model.password)
    db.commit()
    db.refresh(user)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content="Password successfully reset"
    )