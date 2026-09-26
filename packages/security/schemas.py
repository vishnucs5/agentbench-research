from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserRole(str, PyEnum):
    VIEWER = "viewer"
    RESEARCHER = "researcher"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class Permission(str, PyEnum):
    READ_PROJECTS = "read:projects"
    WRITE_PROJECTS = "write:projects"
    DELETE_PROJECTS = "delete:projects"
    READ_PAPERS = "read:papers"
    WRITE_PAPERS = "write:papers"
    DELETE_PAPERS = "delete:papers"
    RUN_EXTRACTION = "run:extraction"
    RUN_RETRIEVAL = "run:retrieval"
    RUN_SYNTHESIS = "run:synthesis"
    RUN_VERIFICATION = "run:verification"
    RUN_EVALUATION = "run:evaluation"
    MANAGE_USERS = "manage:users"
    VIEW_AUDIT_LOGS = "view:audit_logs"
    MANAGE_SYSTEM = "manage:system"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.VIEWER: {
        Permission.READ_PROJECTS,
        Permission.READ_PAPERS,
        Permission.RUN_RETRIEVAL,
    },
    UserRole.RESEARCHER: {
        Permission.READ_PROJECTS,
        Permission.WRITE_PROJECTS,
        Permission.READ_PAPERS,
        Permission.WRITE_PAPERS,
        Permission.RUN_EXTRACTION,
        Permission.RUN_RETRIEVAL,
        Permission.RUN_SYNTHESIS,
        Permission.RUN_VERIFICATION,
    },
    UserRole.SUPERVISOR: {
        Permission.READ_PROJECTS,
        Permission.WRITE_PROJECTS,
        Permission.DELETE_PROJECTS,
        Permission.READ_PAPERS,
        Permission.WRITE_PAPERS,
        Permission.DELETE_PAPERS,
        Permission.RUN_EXTRACTION,
        Permission.RUN_RETRIEVAL,
        Permission.RUN_SYNTHESIS,
        Permission.RUN_VERIFICATION,
        Permission.RUN_EVALUATION,
        Permission.VIEW_AUDIT_LOGS,
    },
    UserRole.ADMIN: set(Permission),
}


class TokenPayload(BaseModel):
    sub: str
    user_id: UUID
    email: str
    role: UserRole
    permissions: list[Permission]
    exp: int
    iat: int
    jti: str


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: UUID
    email: str
    role: UserRole
    refresh_token: str | None = None


class RegisterRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=255)
    role: UserRole = UserRole.RESEARCHER


class UserResponse(BaseModel):
    user_id: UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: datetime | None


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class AuditEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    user_id: UUID | None = None
    action: str
    resource_type: str | None = None
    resource_id: UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    status: str  # "success", "failure"
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RateLimitConfig(BaseModel):
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10


class SecurityConfig(BaseModel):
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    password_require_special: bool = True
    password_disallow_common: bool = True
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    ip_max_login_attempts: int = 20
    ip_lockout_duration_minutes: int = 30
    session_timeout_minutes: int = 60
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    cors_allowed_origins: list[str] = Field(default_factory=list)
    allowed_hosts: list[str] = Field(default_factory=list)


def get_role_permissions(role: UserRole) -> set[Permission]:
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: UserRole, permission: Permission) -> bool:
    return permission in get_role_permissions(role)


def check_permissions(role: UserRole, required: set[Permission]) -> bool:
    user_perms = get_role_permissions(role)
    return required.issubset(user_perms)
