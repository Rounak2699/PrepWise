from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models import User
from ..schemas import ProfileIn, UserOut
from .deps import get_current_user
from .serializers import user_out

router = APIRouter(prefix="/api/me", tags=["profile"])


@router.get("", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.patch("", response_model=UserOut)
def update_me(payload: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True, exclude={"preferences"})
    for field, value in data.items():
        setattr(user, field, value)

    if payload.preferences is not None:
        prefs = user.preferences
        for field, value in payload.preferences.model_dump(exclude_unset=True).items():
            setattr(prefs, field, value)

    db.commit()
    db.refresh(user)
    return user_out(user)
