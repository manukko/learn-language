from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.services.auth import (
    get_db_session,
    get_current_user_factory
)
from src.db.models import User
from src.schemas.stats import StatOutputModel
from src.services.stats import StatService

router = APIRouter()
stats_service = StatService()

@router.get("/", response_model=List[StatOutputModel])
def get_stats_for_user(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_factory()),
    language: str | None = Query(None)
    ):
    stats = stats_service.get_stats_for_user(db, current_user, language)
    return stats
