import uuid
from typing import Dict, List, Optional, Protocol, Callable

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import UserRead, UserCreate, UserUpdate, UserRole
from app.models.common import PaginatedResponse
from app.services.orm_models import UserORM


class UserServiceProtocol(Protocol):
    def list_users(
        self,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> PaginatedResponse[UserRead]:
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

    def list_users(
        self,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> PaginatedResponse[UserRead]:
        with self.session_factory() as session:
            query = session.query(UserORM)
            
            # Apply filters
            query = self._apply_filters(
                query,
                email=email,
                full_name=full_name,
                role=role,
                search=search,
            )
            
            # Get total count before pagination
            total = query.count()
            
            # Apply sorting
            query = self._apply_sorting(query, sort_by, sort_order)
            
            # Apply pagination
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit)
            
            # Execute query
            rows = query.all()
            items = [
                UserRead(
                    id=row.user_id,
                    email=row.email,
                    full_name=row.username,
                    primary_phone=row.phone,
                    role=UserRole(row.role) if row.role else UserRole.user
                ) for row in rows
            ]
            
            # Calculate pagination metadata
            total_pages = (total + limit - 1) // limit if total > 0 else 0
            has_next = page < total_pages
            has_prev = page > 1
            
            return PaginatedResponse(
                items=items,
                total=total,
                page=page,
                limit=limit,
                total_pages=total_pages,
                has_next=has_next,
                has_prev=has_prev,
            )
    
    def _apply_filters(
        self,
        query,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        search: Optional[str] = None,
    ):
        """Apply filtering conditions to the query."""
        if email:
            query = query.filter(UserORM.email.ilike(f"%{email}%"))
        
        if full_name:
            query = query.filter(UserORM.username.ilike(f"%{full_name}%"))
        
        if role:
            query = query.filter(UserORM.role == role)
        
        if search:
            # Search in email, username, and phone
            search_filter = or_(
                UserORM.email.ilike(f"%{search}%"),
                UserORM.username.ilike(f"%{search}%"),
                UserORM.phone.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)
        
        return query
    
    def _apply_sorting(self, query, sort_by: Optional[str] = None, sort_order: Optional[str] = None):
        """Apply sorting to the query."""
        # Default sorting by created_at descending (newest first)
        if not sort_by:
            return query.order_by(UserORM.created_at.desc())
        
        # Map sort_by field names to ORM columns
        sort_mapping = {
            "id": UserORM.user_id,
            "email": UserORM.email,
            "full_name": UserORM.username,
            "role": UserORM.role,
            "created_at": UserORM.created_at,
        }
        
        sort_column = sort_mapping.get(sort_by.lower())
        if not sort_column:
            # Invalid sort_by, use default
            return query.order_by(UserORM.created_at.desc())
        
        # Apply sort order
        if sort_order and sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        return query

    def get_user(self, user_id: str) -> Optional[UserRead]:
        with self.session_factory() as session:
            row = session.get(UserORM, user_id)
            if not row:
                return None
            return UserRead(
                id=row.user_id, 
                email=row.email, 
                full_name=row.username, 
                primary_phone=row.phone,
                role=UserRole(row.role) if row.role else UserRole.user
            )

    def get_user_by_google_id(self, google_id: str) -> Optional[UserRead]:
        """Get user by Google ID"""
        with self.session_factory() as session:
            row = session.query(UserORM).filter(UserORM.google_id == google_id).first()
            if not row:
                return None
            return UserRead(
                id=row.user_id, 
                email=row.email, 
                full_name=row.username, 
                primary_phone=row.phone,
                role=UserRole(row.role) if row.role else UserRole.user
            )

    def get_user_by_email(self, email: str) -> Optional[UserRead]:
        """Get user by email"""
        with self.session_factory() as session:
            row = session.query(UserORM).filter(UserORM.email == email).first()
            if not row:
                return None
            return UserRead(
                id=row.user_id, 
                email=row.email, 
                full_name=row.username, 
                primary_phone=row.phone,
                role=UserRole(row.role) if row.role else UserRole.user
            )

    def create_user(self, payload: UserCreate) -> UserRead:
        with self.session_factory() as session:
            new_row = UserORM(
                user_id=str(uuid.uuid4()),
                username=payload.full_name,  # Map full_name to username
                email=payload.email,
                phone=payload.primary_phone,  # Map primary_phone to phone
                role="user",  # Default role
            )
            session.add(new_row)
            session.commit()
            session.refresh(new_row)
            self.logger.info("user_created", user_id=new_row.user_id)
            return UserRead(
                id=new_row.user_id, 
                email=new_row.email, 
                full_name=new_row.username, 
                primary_phone=new_row.phone,
                role=UserRole(new_row.role) if new_row.role else UserRole.user
            )

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
                role="user",  # Default role
            )
            session.add(new_row)
            session.commit()
            session.refresh(new_row)
            self.logger.info("user_created_from_google", user_id=new_row.user_id, google_id=google_id, email=email)
            return UserRead(
                id=new_row.user_id, 
                email=new_row.email, 
                full_name=new_row.username, 
                primary_phone=new_row.phone,
                role=UserRole(new_row.role) if new_row.role else UserRole.user
            )

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
            return UserRead(
                id=row.user_id, 
                email=row.email, 
                full_name=row.username, 
                primary_phone=row.phone,
                role=UserRole(row.role) if row.role else UserRole.user
            )

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
            return UserRead(
                id=row.user_id, 
                email=row.email, 
                full_name=row.username, 
                primary_phone=row.phone,
                role=UserRole(row.role) if row.role else UserRole.user
            )

    def delete_user(self, user_id: str) -> bool:
        with self.session_factory() as session:
            row = session.get(UserORM, user_id)
            if not row:
                return False
            session.delete(row)
            session.commit()
            self.logger.info("user_deleted", user_id=user_id)
            return True