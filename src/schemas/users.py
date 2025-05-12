from datetime import datetime
from typing import List
from pydantic import BaseModel



class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserModel(BaseModel):
    username: str
    email: str
    created_at: datetime
    updated_at: datetime

class EmailModel(BaseModel):
    addresses: List[str]

class SendResetPasswordLinkModel(BaseModel):
    email: str

class ResetPasswordModel(BaseModel):
    password: str
    confirm_password: str