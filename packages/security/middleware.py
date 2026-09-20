from __future__ import annotations

import time

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from packages.domain.database import get_db_session, get_session
from packages.domain.models import User
from packages.security.auth import AuthService, get_auth_service
from packages.security.schemas import Permission, UserRole, get_role_permissions
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

security = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, auth_service: AuthService | None = None):
        super().__init__(app)
        self.auth_service = auth_service or get_auth_service()
        self.exempt_paths = {
            "/",
            "/healthz",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/dashboard",
            "/app",
            "/ui",
            "/v1/auth/login",
            "/v1/auth/register",
            "/v1/auth/refresh",
        }

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exempt_paths or request.url.path.startswith(("/static", "/dashboard", "/app", "/ui")):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return self._unauthorized("Missing or invalid authorization header")

        token = auth_header.split(" ")[1]
        payload = self.auth_service.decode_token(token)
        if not payload:
            return self._unauthorized("Invalid or expired token")

        async with get_session() as session:
            result = await session.execute(select(User).where(User.id == payload.user_id))
            user = result.scalar_one_or_none()
            if not user or not user.is_active:
                return self._unauthorized("User not found or inactive")

            request.state.user = user
            request.state.token_payload = payload

        return await call_next(request)

    def _unauthorized(self, message: str) -> Response:
        return Response(
            content='{"detail": "' + message + '"}',
            status_code=status.HTTP_401_UNAUTHORIZED,
            media_type="application/json",
            headers={"WWW-Authenticate": "Bearer"},
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_buckets: dict[str, list[float]] = {}
        self.hour_buckets: dict[str, list[float]] = {}

    def _get_client_id(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_buckets(self, buckets: dict[str, list[float]], window: float) -> None:
        now = time.time()
        for key in list(buckets.keys()):
            buckets[key] = [t for t in buckets[key] if now - t < window]
            if not buckets[key]:
                del buckets[key]

    async def dispatch(self, request: Request, call_next):
        client_id = self._get_client_id(request)
        now = time.time()

        self._clean_buckets(self.minute_buckets, 60)
        self._clean_buckets(self.hour_buckets, 3600)

        if client_id not in self.minute_buckets:
            self.minute_buckets[client_id] = []
        if client_id not in self.hour_buckets:
            self.hour_buckets[client_id] = []

        if len(self.minute_buckets[client_id]) >= 60:
            return Response(
                content='{"detail": "Rate limit exceeded: too many requests per minute"}',
                status_code=429,
                media_type="application/json",
            )

        if len(self.hour_buckets[client_id]) >= 1000:
            return Response(
                content='{"detail": "Rate limit exceeded: too many requests per hour"}',
                status_code=429,
                media_type="application/json",
            )

        self.minute_buckets[client_id].append(now)
        self.hour_buckets[client_id].append(now)

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        return response


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth_service.decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with get_session() as session:
        from packages.domain.models import User
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == payload.user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        return user


def require_permission(permission: Permission):
    def checker(user: User = Depends(get_current_user)) -> User:
        user_permissions = get_role_permissions(user.role)
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required",
            )
        return user
    return checker


def require_role(role: UserRole):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role != role and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {role.value} or admin required",
            )
        return user
    return checker


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> User | None:
    if not credentials:
        return None
    payload = auth_service.decode_token(credentials.credentials)
    if not payload:
        return None
    async with get_session() as session:
        from packages.domain.models import User
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == payload.user_id))
        return result.scalar_one_or_none()
