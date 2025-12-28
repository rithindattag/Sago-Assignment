from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Startup
from ..schemas import StartupCreate, StartupRead

router = APIRouter(prefix="/startups", tags=["startups"])


@router.post("", response_model=StartupRead, status_code=status.HTTP_201_CREATED)
def create_startup(payload: StartupCreate, db: Session = Depends(get_db)) -> StartupRead:
    startup = Startup(
        name=payload.name,
        domain=payload.domain,
        founder_email=payload.founder_email,
        status=payload.status,
    )
    try:
        db.add(startup)
        db.commit()
        db.refresh(startup)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Startup could not be created.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating startup.",
        ) from exc
    return startup


@router.get("", response_model=List[StartupRead])
def list_startups(db: Session = Depends(get_db)) -> List[StartupRead]:
    result = db.execute(select(Startup).order_by(Startup.created_at.desc()))
    return result.scalars().all()


@router.get("/{startup_id}", response_model=StartupRead)
def get_startup(startup_id: UUID, db: Session = Depends(get_db)) -> StartupRead:
    startup = db.get(Startup, startup_id)
    if not startup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Startup not found.",
        )
    return startup
