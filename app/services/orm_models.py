from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime
from datetime import datetime


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), index=True, unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
