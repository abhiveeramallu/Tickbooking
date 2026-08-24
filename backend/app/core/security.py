from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(value: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC.

    Some backends (notably SQLite, used in tests) do not preserve tzinfo on
    round-trip even when the column is declared DateTime(timezone=True).
    Values read back as naive are assumed to already be UTC. PostgreSQL in
    production returns proper aware datetimes, so this is a no-op there.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: dict, expires_delta: timedelta | None = None) -> str:
    expire = utcnow() + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    payload = {**subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def safe_decode_access_token(token: str) -> dict | None:
    try:
        return decode_access_token(token)
    except JWTError:
        return None

