import uuid
from typing import Dict, List, Optional, Protocol, Callable

from sqlalchemy.orm import Session

from app.models.user import UserRead, UserCreate, UserUpdate
from app.services.orm_models import UserORM


class UserServiceProtocol(Protocol):
    def list_users(self) -> List[UserRead]:
        ...

    def get_user(self, user_id: str) -> Optional[UserRead]:
        ...

    def get_user_by_google_id(self, google_id: str) -> Optional[UserRead]:
        ...

    def get_user_by_email(self, email: str) -> Optional[UserRead]:
        ...

    def create_user(self, payload: UserCreate) -> UserRead:
        ...

    def create_user_from_google(self, google_id: str, email: str, name: Optional[str] = None) -> UserRead:
        ...

    def link_google_id(self, user_id: str, google_id: str) -> Optional[UserRead]:
        ...

    def update_user(self, user_id: str, payload: UserUpdate) -> Optional[UserRead]:
        ...

    def delete_user(self, user_id: str) -> bool:
        ...


class SqlAlchemyUserService:
    def __init__(self, logger, session_factory: Callable[[], Session]):
        self.logger = logger
        self.session_factory = session_factory

    def list_users(self) -> List[UserRead]:
        with self.session_factory() as session:
            rows = session.query(UserORM).all()
            return [UserRead(id=row.user_id, email=row.email, full_name=row.username, primary_phone=row.phone) for row in rows]

    def get_user(self, user_id: str) -> Optional[UserRead]:
        with self.session_factory() as session:
            row = session.get(UserORM, user_id)
            if not row:
                return None
            return UserRead(id=row.user_id, email=row.email, full_name=row.username, primary_phone=row.phone)

    def get_user_by_google_id(self, google_id: str) -> Optional[UserRead]:
        """Get user by Google ID"""
        with self.session_factory() as session:
            row = session.query(UserORM).filter(UserORM.google_id == google_id).first()
            if not row:
                return None
            return UserRead(id=row.user_id, email=row.email, full_name=row.username, primary_phone=row.phone)

    def get_user_by_email(self, email: str) -> Optional[UserRead]:
        """Get user by email"""
        with self.session_factory() as session:
            row = session.query(UserORM).filter(UserORM.email == email).first()
            if not row:
                return None
            return UserRead(id=row.user_id, email=row.email, full_name=row.username, primary_phone=row.phone)

    def create_user(self, payload: UserCreate) -> UserRead:
        with self.session_factory() as session:
            new_row = UserORM(
                user_id=str(uuid.uuid4()),
                username=payload.full_name,  # Map full_name to username
                email=payload.email,
                phone=payload.primary_phone,  # Map primary_phone to phone
            )
            session.add(new_row)
            session.commit()
            session.refresh(new_row)
            self.logger.info("user_created", user_id=new_row.user_id)
            return UserRead(id=new_row.user_id, email=new_row.email, full_name=new_row.username, primary_phone=new_row.phone)

    def create_user_from_google(self, google_id: str, email: str, name: Optional[str] = None) -> UserRead:
        """Create user from Google OAuth information"""
        with self.session_factory() as session:
            # Use name from Google or email as fallback
            username = name or email.split('@')[0]
            
            new_row = UserORM(
                user_id=str(uuid.uuid4()),
                username=username,
                email=email,
                google_id=google_id,
                phone=None,
            )
            session.add(new_row)
            session.commit()
            session.refresh(new_row)
            self.logger.info("user_created_from_google", user_id=new_row.user_id, google_id=google_id, email=email)
            return UserRead(id=new_row.user_id, email=new_row.email, full_name=new_row.username, primary_phone=new_row.phone)

    def update_user(self, user_id: str, payload: UserUpdate) -> Optional[UserRead]:
        with self.session_factory() as session:
            row = session.get(UserORM, user_id)
            if not row:
                return None
            if payload.email is not None:
                row.email = payload.email
            if payload.full_name is not None:
                row.username = payload.full_name  # Map full_name to username
            if payload.primary_phone is not None:
                row.phone = payload.primary_phone  # Map primary_phone to phone
            session.add(row)
            session.commit()
            session.refresh(row)
            self.logger.info("user_updated", user_id=user_id)
            return UserRead(id=row.user_id, email=row.email, full_name=row.username, primary_phone=row.phone)

    def link_google_id(self, user_id: str, google_id: str) -> Optional[UserRead]:
        """Link Google ID to existing user account"""
        with self.session_factory() as session:
            row = session.get(UserORM, user_id)
            if not row:
                return None
            row.google_id = google_id
            session.add(row)
            session.commit()
            session.refresh(row)
            self.logger.info("google_id_linked", user_id=user_id, google_id=google_id)
            return UserRead(id=row.user_id, email=row.email, full_name=row.username, primary_phone=row.phone)

    def delete_user(self, user_id: str) -> bool:
        with self.session_factory() as session:
            row = session.get(UserORM, user_id)
            if not row:
                return False
            session.delete(row)
            session.commit()
            self.logger.info("user_deleted", user_id=user_id)
            return True