from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.v1.deps import UserServiceDep
from app.schemas.user import (
    InterestAssignRequest,
    UserCreate,
    UserInterestRead,
    UserRead,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, service: UserServiceDep) -> UserRead:
    user = await service.create_user(payload)
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: UUID, service: UserServiceDep) -> UserRead:
    return UserRead.model_validate(await service.get_user(user_id))


@router.post(
    "/{user_id}/interests",
    response_model=list[UserInterestRead],
    status_code=status.HTTP_201_CREATED,
)
async def assign_interests(
    user_id: UUID, payload: InterestAssignRequest, service: UserServiceDep
) -> list[UserInterestRead]:
    links = await service.assign_interests(user_id, payload.items)
    return [
        UserInterestRead(name=link.interest.name, weight=link.weight, created_at=link.created_at)
        for link in links
    ]


@router.get("/{user_id}/interests", response_model=list[UserInterestRead])
async def list_interests(user_id: UUID, service: UserServiceDep) -> list[UserInterestRead]:
    links = await service.list_interests(user_id)
    return [
        UserInterestRead(name=link.interest.name, weight=link.weight, created_at=link.created_at)
        for link in links
    ]


@router.delete("/{user_id}/interests/{interest_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_interest(user_id: UUID, interest_name: str, service: UserServiceDep) -> None:
    await service.remove_interest(user_id, interest_name)
