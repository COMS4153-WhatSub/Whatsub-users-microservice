import uuid
from typing import Dict, List, Optional, Protocol, Callable

from sqlalchemy.orm import Session

from app.models.user import User, UserCreate, UserUpdate
from app.services.orm_models import UserORM


class InMemoryUserService:
    def __init__(self, logger):
        self.logger = logger
        self.users: Dict[str, Dict] = {}

    def list_users(self) -> List[User]:
        return [User(**user) for user in self.users.values()]

    def get_user(self, user_id: str) -> Optional[User]:
        data = self.users.get(user_id)
        return User(**data) if data else None

    def create_user(self, payload: UserCreate) -> User:
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": payload.email,
            "full_name": payload.full_name,
            "primary_phone": payload.primary_phone,
        }
        # NOTE: Do not store plaintext passwords; this is a placeholder for demo
        self.users[user_id] = user
        self.logger.info("user_created", user_id=user_id)
        return User(**user)

    def update_user(self, user_id: str, payload: UserUpdate) -> Optional[User]:
        existing = self.users.get(user_id)
        if not existing:
            return None
        if payload.email is not None:
            existing["email"] = payload.email
        if payload.full_name is not None:
            existing["full_name"] = payload.full_name
        if payload.primary_phone is not None:
            existing["primary_phone"] = payload.primary_phone
        self.users[user_id] = existing
        self.logger.info("user_updated", user_id=user_id)
        return User(**existing)

    def delete_user(self, user_id: str) -> bool:
        if user_id in self.users:
            del self.users[user_id]
            self.logger.info("user_deleted", user_id=user_id)
            return True
        return False


class UserServiceProtocol(Protocol):
    def list_users(self) -> List[User]:
        ...

    def get_user(self, user_id: str) -> Optional[User]:
        ...

    def create_user(self, payload: UserCreate) -> User:
        ...

    def update_user(self, user_id: str, payload: UserUpdate) -> Optional[User]:
        ...

    def delete_user(self, user_id: str) -> bool:
        ...


class SqlAlchemyUserService:
    def __init__(self, logger, session_factory: Callable[[], Session]):
        self.logger = logger
        self.session_factory = session_factory

    def list_users(self) -> List[User]:
        with self.session_factory() as session:
            rows = session.query(UserORM).all()
            return [User(id=row.id, email=row.email, full_name=row.full_name, primary_phone=row.primary_phone) for row in rows]

    def get_user(self, user_id: str) -> Optional[User]:
        with self.session_factory() as session:
            row = session.get(UserORM, user_id)
            if not row:
                return None
            return User(id=row.id, email=row.email, full_name=row.full_name, primary_phone=row.primary_phone)

    def create_user(self, payload: UserCreate) -> User:
        with self.session_factory() as session:
            new_row = UserORM(
                id=str(uuid.uuid4()),
                email=payload.email,
                full_name=payload.full_name,
                primary_phone=payload.primary_phone,
            )
            session.add(new_row)
            session.commit()
            session.refresh(new_row)
            self.logger.info("user_created", user_id=new_row.id)
            return User(id=new_row.id, email=new_row.email, full_name=new_row.full_name, primary_phone=new_row.primary_phone)

    def update_user(self, user_id: str, payload: UserUpdate) -> Optional[User]:
        with self.session_factory() as session:
            row = session.get(UserORM, user_id)
            if not row:
                return None
            if payload.email is not None:
                row.email = payload.email
            if payload.full_name is not None:
                row.full_name = payload.full_name
            if payload.primary_phone is not None:
                row.primary_phone = payload.primary_phone
            session.add(row)
            session.commit()
            session.refresh(row)
            self.logger.info("user_updated", user_id=user_id)
            return User(id=row.id, email=row.email, full_name=row.full_name, primary_phone=row.primary_phone)

    def delete_user(self, user_id: str) -> bool:
        with self.session_factory() as session:
            row = session.get(UserORM, user_id)
            if not row:
                return False
            session.delete(row)
            session.commit()
            self.logger.info("user_deleted", user_id=user_id)
            return True