from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from packages.security.auth import AuthService, get_auth_service
from packages.security.middleware import get_current_user
from packages.security.schemas import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    RegisterRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserResponse,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    request: LoginRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    response = await auth_service.login(
        request, ip_address=http_request.client.host if http_request.client else None
    )
    if not response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account locked",
        )
    return response


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return await auth_service.register(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_token(
    request: TokenRefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    response = await auth_service.refresh_token(request)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return response


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
)
async def change_password(
    request: PasswordChangeRequest,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        success = await auth_service.change_password(current_user.id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password incorrect",
        )
    return {"detail": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user=Depends(get_current_user),
):
    return UserResponse(
        user_id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    auth_service.revoke_all_refresh_tokens(current_user.id)
    return {"detail": "Logged out successfully"}
