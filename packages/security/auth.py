from __future__ import annotations

import secrets
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from packages.domain.config import get_settings
from packages.security.schemas import (
    AuditEvent,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    RegisterRequest,
    SecurityConfig,
    TokenPayload,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserResponse,
    UserRole,
    get_role_permissions,
)
from pydantic import ValidationError

DISALLOWED_COMMON_PASSWORDS: set[str] = {
    "password",
    "password123",
    "password1234",
    "admin1234",
    "12345678",
    "qwerty1234",
    "welcome123",
    "letmein123",
    "agentbench123",
}


class AuthService:
    def __init__(self, config: SecurityConfig | None = None):
        self.config = config or self._default_config()
        self._failed_attempts: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}
        self._ip_failed_attempts: dict[str, list[float]] = {}
        self._ip_locked_until: dict[str, float] = {}
        self._refresh_tokens: dict[str, dict[str, Any]] = {}

    def _default_config(self) -> SecurityConfig:
        settings = get_settings()
        return SecurityConfig(
            jwt_secret_key=settings.secret_key,
            jwt_algorithm=settings.jwt_algorithm,
            access_token_expire_minutes=settings.access_token_expire_minutes,
        )

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def validate_password_strength(
        self, password: str, user_email: str | None = None
    ) -> tuple[bool, str | None]:
        if len(password) < self.config.password_min_length:
            return False, f"Password must be at least {self.config.password_min_length} characters"
        if len(password) > 128:
            return False, "Password cannot exceed 128 characters"

        if getattr(self.config, "password_disallow_common", True):
            normalized = password.strip().lower()
            if normalized in DISALLOWED_COMMON_PASSWORDS or any(
                p in normalized for p in ("password", "123456", "admin123")
            ):
                return False, "Password is too common and easily guessed"
            if user_email and "@" in user_email:
                local_part = user_email.split("@")[0].lower()
                if len(local_part) >= 4 and local_part in normalized:
                    return False, "Password must not contain parts of your email address"

        if self.config.password_require_uppercase and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        if self.config.password_require_lowercase and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        if self.config.password_require_digits and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        if self.config.password_require_special and not any(
            c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password
        ):
            return False, "Password must contain at least one special character"

        return True, None

    def is_locked(self, identifier: str) -> bool:
        if identifier in self._locked_until:
            if time.time() < self._locked_until[identifier]:
                return True
            else:
                del self._locked_until[identifier]
        return False

    def is_ip_locked(self, ip_address: str) -> bool:
        if ip_address in self._ip_locked_until:
            if time.time() < self._ip_locked_until[ip_address]:
                return True
            else:
                del self._ip_locked_until[ip_address]
        return False

    def record_failed_attempt(self, identifier: str) -> None:
        now = time.time()
        if identifier not in self._failed_attempts:
            self._failed_attempts[identifier] = []
        self._failed_attempts[identifier] = [
            t for t in self._failed_attempts[identifier] if now - t < 3600
        ]
        self._failed_attempts[identifier].append(now)

        if len(self._failed_attempts[identifier]) >= self.config.max_login_attempts:
            self._locked_until[identifier] = now + (self.config.lockout_duration_minutes * 60)

    def record_ip_failed_attempt(self, ip_address: str) -> None:
        now = time.time()
        if ip_address not in self._ip_failed_attempts:
            self._ip_failed_attempts[ip_address] = []
        self._ip_failed_attempts[ip_address] = [
            t for t in self._ip_failed_attempts[ip_address] if now - t < 3600
        ]
        self._ip_failed_attempts[ip_address].append(now)

        max_ip_attempts = getattr(self.config, "ip_max_login_attempts", 20)
        lockout_mins = getattr(self.config, "ip_lockout_duration_minutes", 30)
        if len(self._ip_failed_attempts[ip_address]) >= max_ip_attempts:
            self._ip_locked_until[ip_address] = now + (lockout_mins * 60)

    def clear_failed_attempts(self, identifier: str) -> None:
        if identifier in self._failed_attempts:
            del self._failed_attempts[identifier]
        if identifier in self._locked_until:
            del self._locked_until[identifier]

    def clear_ip_failed_attempts(self, ip_address: str) -> None:
        if ip_address in self._ip_failed_attempts:
            del self._ip_failed_attempts[ip_address]
        if ip_address in self._ip_locked_until:
            del self._ip_locked_until[ip_address]

    def create_access_token(self, payload: TokenPayload) -> str:
        data = payload.model_dump(mode="json")
        # Ensure UUIDs are strings for JWT
        data["user_id"] = str(payload.user_id)
        data["permissions"] = [
            p.value if hasattr(p, "value") else str(p) for p in payload.permissions
        ]
        data["role"] = payload.role.value if hasattr(payload.role, "value") else str(payload.role)
        return jwt.encode(
            data,
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm,
        )

    def create_refresh_token(self, user_id: UUID) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + (self.config.refresh_token_expire_days * 86400)
        self._refresh_tokens[token] = {
            "user_id": str(user_id),
            "created_at": time.time(),
            "expires_at": expires_at,
        }
        return token

    def verify_refresh_token(self, token: str) -> UUID | None:
        if token not in self._refresh_tokens:
            return None
        data = self._refresh_tokens[token]
        if time.time() > data["expires_at"]:
            del self._refresh_tokens[token]
            return None
        return UUID(data["user_id"])

    def revoke_refresh_token(self, token: str) -> bool:
        if token in self._refresh_tokens:
            del self._refresh_tokens[token]
            return True
        return False

    def decode_token(self, token: str) -> TokenPayload | None:
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
            )
            return TokenPayload(**payload)
        except (jwt.PyJWTError, ValidationError):
            return None

    async def login(
        self, request: LoginRequest, ip_address: str | None = None
    ) -> LoginResponse | None:
        from packages.domain.database import get_session
        from packages.domain.models import User
        from sqlalchemy import select

        if ip_address and self.is_ip_locked(ip_address):
            await self._log_audit(
                user_id=None,
                action="login",
                status="failure",
                error_message="IP address temporarily locked due to too many failed attempts",
                ip_address=ip_address,
            )
            return None

        if self.is_locked(request.email):
            await self._log_audit(
                user_id=None,
                action="login",
                status="failure",
                error_message="Account locked due to too many failed attempts",
                ip_address=ip_address,
            )
            return None

        async with get_session() as session:
            result = await session.execute(select(User).where(User.email == request.email))
            user = result.scalar_one_or_none()

            if not user or not self.verify_password(request.password, user.hashed_password):
                self.record_failed_attempt(request.email)
                if ip_address:
                    self.record_ip_failed_attempt(ip_address)
                await self._log_audit(
                    user_id=user.id if user else None,
                    action="login",
                    status="failure",
                    error_message="Invalid credentials",
                    ip_address=ip_address,
                )
                return None

            if not user.is_active:
                await self._log_audit(
                    user_id=user.id,
                    action="login",
                    status="failure",
                    error_message="Account inactive",
                    ip_address=ip_address,
                )
                return None

            self.clear_failed_attempts(request.email)
            if ip_address:
                self.clear_ip_failed_attempts(ip_address)

            permissions = get_role_permissions(user.role)
            now = int(time.time())
            payload = TokenPayload(
                sub=str(user.id),
                user_id=user.id,
                email=user.email,
                role=user.role,
                permissions=list(permissions),
                exp=now + (self.config.access_token_expire_minutes * 60),
                iat=now,
                jti=secrets.token_urlsafe(16),
            )

            access_token = self.create_access_token(payload)
            refresh_token = self.create_refresh_token(user.id)

            user.last_login = datetime.now(UTC)
            await session.flush()

            await self._log_audit(
                user_id=user.id,
                action="login",
                status="success",
                ip_address=ip_address,
            )

            return LoginResponse(
                access_token=access_token,
                expires_in=self.config.access_token_expire_minutes * 60,
                user_id=user.id,
                email=user.email,
                role=user.role,
                refresh_token=refresh_token,
            )

    async def register(
        self, request: RegisterRequest, requester_role: UserRole | str | None = None
    ) -> UserResponse:
        from packages.domain.database import get_session
        from packages.domain.models import User
        from sqlalchemy import select

        valid, error = self.validate_password_strength(request.password, request.email)
        if not valid:
            raise ValueError(error)

        # Privilege fix: only ADMIN can create ADMIN/SUPERVISOR accounts.
        role = UserRole.RESEARCHER
        effective_requester: UserRole | None = None
        if isinstance(requester_role, UserRole):
            effective_requester = requester_role
        elif isinstance(requester_role, str):
            try:
                effective_requester = UserRole(requester_role)
            except ValueError:
                effective_requester = None
        if (
            request.role in (UserRole.ADMIN, UserRole.SUPERVISOR)
            and effective_requester == UserRole.ADMIN
        ):
            role = request.role

        async with get_session() as session:
            result = await session.execute(select(User).where(User.email == request.email))
            if result.scalar_one_or_none():
                raise ValueError("Email already registered")

            hashed = self.hash_password(request.password)
            import hashlib

            email_hash = hashlib.sha256(request.email.lower().encode()).hexdigest()
            display_name = request.full_name or request.email.split("@")[0]
            user = User(
                email=request.email,
                email_hash=email_hash,
                hashed_password=hashed,
                password_history=[hashed],
                full_name=request.full_name,
                display_name=display_name,
                role=role,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            await self._log_audit(
                user_id=user.id,
                action="register",
                status="success",
            )

            return UserResponse(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login,
            )

    async def refresh_token(self, request: TokenRefreshRequest) -> TokenRefreshResponse | None:
        user_id = self.verify_refresh_token(request.refresh_token)
        if not user_id:
            return None

        from packages.domain.database import get_session
        from packages.domain.models import User
        from sqlalchemy import select

        async with get_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user or not user.is_active:
                return None

            permissions = get_role_permissions(user.role)
            now = int(time.time())
            payload = TokenPayload(
                sub=str(user.id),
                user_id=user.id,
                email=user.email,
                role=user.role,
                permissions=list(permissions),
                exp=now + (self.config.access_token_expire_minutes * 60),
                iat=now,
                jti=secrets.token_urlsafe(16),
            )

            access_token = self.create_access_token(payload)
            new_refresh_token = self.create_refresh_token(user.id)
            self.revoke_refresh_token(request.refresh_token)

            return TokenRefreshResponse(
                access_token=access_token,
                expires_in=self.config.access_token_expire_minutes * 60,
                refresh_token=new_refresh_token,
            )

    async def change_password(self, user_id: UUID, request: PasswordChangeRequest) -> bool:
        from packages.domain.database import get_session
        from packages.domain.models import User
        from sqlalchemy import select

        if request.new_password == request.current_password:
            raise ValueError("New password cannot be identical to current password")

        valid, error = self.validate_password_strength(request.new_password)
        if not valid:
            raise ValueError(error)

        async with get_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user or not self.verify_password(request.current_password, user.hashed_password):
                return False

            history = list(getattr(user, "password_history", None) or [user.hashed_password])
            for past_hash in history[:5]:
                if self.verify_password(request.new_password, past_hash):
                    raise ValueError("Cannot reuse any of your last 5 passwords")

            valid, error = self.validate_password_strength(request.new_password, user.email)
            if not valid:
                raise ValueError(error)

            new_hashed = self.hash_password(request.new_password)
            user.hashed_password = new_hashed
            user.password_history = ([new_hashed] + history)[:5]
            await session.commit()

            self.revoke_all_refresh_tokens(user_id)

            await self._log_audit(
                user_id=user_id,
                action="password_change",
                status="success",
            )

            return True

    def revoke_all_refresh_tokens(self, user_id: UUID) -> int:
        revoked = 0
        for token, data in list(self._refresh_tokens.items()):
            if data["user_id"] == str(user_id):
                del self._refresh_tokens[token]
                revoked += 1
        return revoked

    async def _log_audit(
        self,
        user_id: UUID | None,
        action: str,
        status: str,
        error_message: str | None = None,
        ip_address: str | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
    ) -> None:
        AuditEvent(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            status=status,
            error_message=error_message,
        )
        # In production, write to audit log table
        pass


_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def reset_auth_service() -> None:
    global _auth_service
    _auth_service = None
