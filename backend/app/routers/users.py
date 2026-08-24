from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.user import UserResponse
from app.services.auth_service import get_current_user


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)

