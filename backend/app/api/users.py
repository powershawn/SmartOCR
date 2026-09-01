from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.schemas.auth import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    users = await db.scalars(select(User).order_by(User.name))
    return [
        UserOut(id=str(user.id), email=user.email, name=user.name, picture=user.picture, role=user.role)
        for user in users.all()
    ]

