from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.db.models import UserAccount, UserSession
from app.db.session import get_db_session


class AuthRepository:
    def create_user(self, email: str, full_name: str, password_hash: str, password_salt: str) -> UserAccount:
        with get_db_session() as session:
            user = UserAccount(
                email=email.lower(),
                full_name=full_name,
                password_hash=password_hash,
                password_salt=password_salt,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def get_user_by_email(self, email: str) -> UserAccount | None:
        with get_db_session() as session:
            return session.scalar(select(UserAccount).where(UserAccount.email == email.lower()))

    def get_user_by_id(self, user_id: int) -> UserAccount | None:
        with get_db_session() as session:
            return session.get(UserAccount, user_id)

    def get_user_by_token(self, token: str) -> UserAccount | None:
        with get_db_session() as session:
            # Use joinedload to fetch user in the same query
            from sqlalchemy.orm import joinedload
            user_session = session.scalar(
                select(UserSession)
                .options(joinedload(UserSession.user))
                .where(UserSession.access_token == token)
            )
            if user_session is None:
                return None
            if user_session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                session.delete(user_session)
                session.commit()
                return None
            # The session will close, but user object is already loaded.
            # However, it's safer to return the UserAccount object as is OR ensure it's loaded.
            return user_session.user

    def create_session(self, user_id: int, access_token: str, expires_at: datetime) -> UserSession:
        with get_db_session() as session:
            user_session = UserSession(user_id=user_id, access_token=access_token, expires_at=expires_at)
            session.add(user_session)
            user = session.get(UserAccount, user_id)
            if user is not None:
                user.last_login_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(user_session)
            return user_session

    def revoke_session(self, access_token: str) -> None:
        with get_db_session() as session:
            session.execute(delete(UserSession).where(UserSession.access_token == access_token))
            session.commit()
