"""
JWT-based authentication for CHAT.
Designed to be swappable with other auth providers (e.g., LDAP, Active Directory).
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from chat.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from chat.db.models import User, authenticate_user, get_user_by_id, create_user


@dataclass
class AuthResult:
    """Result of an authentication attempt."""
    success: bool
    user: Optional[User] = None
    token: Optional[str] = None
    error: Optional[str] = None


class AuthProvider:
    """
    Base authentication provider interface.
    Subclass this to implement different auth backends (LDAP, OAuth, etc.)
    """

    def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate a user and return a result with JWT token."""
        raise NotImplementedError

    def register(self, username: str, email: str, password: str) -> AuthResult:
        """Register a new user."""
        raise NotImplementedError

    def validate_token(self, token: str) -> Optional[User]:
        """Validate a JWT token and return the user if valid."""
        raise NotImplementedError

    def refresh_token(self, token: str) -> Optional[str]:
        """Refresh an existing token."""
        raise NotImplementedError


class JWTAuthProvider(AuthProvider):
    """
    JWT-based authentication using local SQLite database.
    This can be swapped out for LDAP/AD integration later.
    """

    def __init__(self):
        self.secret_key = JWT_SECRET_KEY
        self.algorithm = JWT_ALGORITHM
        self.expiration_hours = JWT_EXPIRATION_HOURS

    def _create_token(self, user: User) -> str:
        """Create a JWT token for a user."""
        payload = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "exp": datetime.utcnow() + timedelta(hours=self.expiration_hours),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate a user with username and password."""
        user = authenticate_user(username, password)

        if user:
            token = self._create_token(user)
            return AuthResult(success=True, user=user, token=token)
        else:
            return AuthResult(success=False, error="Invalid username or password")

    def register(self, username: str, email: str, password: str) -> AuthResult:
        """Register a new user."""
        # Validate inputs
        if not username or len(username) < 3:
            return AuthResult(success=False, error="Username must be at least 3 characters")

        if not email or "@" not in email:
            return AuthResult(success=False, error="Please enter a valid email address")

        if not password or len(password) < 8:
            return AuthResult(success=False, error="Password must be at least 8 characters")

        # Attempt to create user
        user = create_user(username, email, password)

        if user:
            token = self._create_token(user)
            return AuthResult(success=True, user=user, token=token)
        else:
            return AuthResult(
                success=False,
                error="Username or email already exists"
            )

    def validate_token(self, token: str) -> Optional[User]:
        """Validate a JWT token and return the user if valid."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("user_id")
            if user_id:
                return get_user_by_id(user_id)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        return None

    def refresh_token(self, token: str) -> Optional[str]:
        """Refresh an existing token if it's still valid."""
        user = self.validate_token(token)
        if user:
            return self._create_token(user)
        return None


# Global auth provider instance - swap this to change auth backend
_auth_provider: Optional[AuthProvider] = None


def get_auth_provider() -> AuthProvider:
    """Get the global auth provider instance."""
    global _auth_provider
    if _auth_provider is None:
        _auth_provider = JWTAuthProvider()
    return _auth_provider


def set_auth_provider(provider: AuthProvider):
    """Set a custom auth provider (for swapping to LDAP/AD later)."""
    global _auth_provider
    _auth_provider = provider
