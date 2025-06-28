import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    """User model for storing user preferences and information"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    timezone = Column(String, default="UTC")
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Conversation(Base):
    """Conversation model for storing chat sessions"""
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # Anonymous users allowed
    session_id = Column(String, index=True)
    state = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Message(Base):
    """Message model for storing individual chat messages"""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

class Booking(Base):
    """Booking model for storing appointment records"""
    __tablename__ = "bookings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String, default="confirmed")  # confirmed, cancelled, rescheduled
    calendar_event_id = Column(String)  # Google Calendar event ID
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DatabaseManager:
    """Database manager for handling all database operations"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def create_user(self, email: str = None, name: str = None, timezone: str = "UTC", preferences: Dict = None) -> User:
        """Create a new user"""
        with self.get_session() as session:
            user = User(
                email=email,
                name=name,
                timezone=timezone,
                preferences=preferences or {}
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        with self.get_session() as session:
            return session.query(User).filter(User.email == email).first()
    
    def create_conversation(self, user_id: Optional[str] = None, session_id: str = None) -> Conversation:
        """Create a new conversation"""
        with self.get_session() as session:
            conversation = Conversation(
                user_id=user_id,
                session_id=session_id or str(uuid.uuid4())
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
            return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        with self.get_session() as session:
            return session.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    def update_conversation_state(self, conversation_id: str, state: Dict) -> bool:
        """Update conversation state"""
        with self.get_session() as session:
            conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                conversation.state = state
                conversation.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
    
    def add_message(self, conversation_id: str, role: str, content: str, extra_data: Dict = None) -> Message:
        """Add a message to conversation"""
        with self.get_session() as session:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                extra_data=extra_data or {}
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            return message
    
    def get_conversation_messages(self, conversation_id: str) -> List[Message]:
        """Get all messages for a conversation"""
        with self.get_session() as session:
            return session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at).all()
    
    def create_booking(
        self, 
        conversation_id: str, 
        title: str, 
        start_time: datetime, 
        end_time: datetime,
        description: str = None,
        user_id: str = None,
        calendar_event_id: str = None,
        metadata: Dict = None
    ) -> Booking:
        """Create a new booking record"""
        with self.get_session() as session:
            booking = Booking(
                conversation_id=conversation_id,
                user_id=user_id,
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                calendar_event_id=calendar_event_id,
                metadata=metadata or {}
            )
            session.add(booking)
            session.commit()
            session.refresh(booking)
            return booking
    
    def get_user_bookings(self, user_id: str) -> List[Booking]:
        """Get all bookings for a user"""
        with self.get_session() as session:
            return session.query(Booking).filter(
                Booking.user_id == user_id,
                Booking.status == "confirmed"
            ).order_by(Booking.start_time).all()
    
    def get_bookings_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Booking]:
        """Get bookings within a date range"""
        with self.get_session() as session:
            return session.query(Booking).filter(
                Booking.start_time >= start_date,
                Booking.start_time <= end_date,
                Booking.status == "confirmed"
            ).all()
    
    def update_booking_status(self, booking_id: str, status: str) -> bool:
        """Update booking status"""
        with self.get_session() as session:
            booking = session.query(Booking).filter(Booking.id == booking_id).first()
            if booking:
                booking.status = status
                booking.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
    
    def get_conversation_history(self, user_id: str = None, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        with self.get_session() as session:
            query = session.query(Conversation)
            if user_id:
                query = query.filter(Conversation.user_id == user_id)
            
            conversations = query.filter(
                Conversation.is_active == True
            ).order_by(Conversation.updated_at.desc()).limit(limit).all()
            
            result = []
            for conv in conversations:
                messages = self.get_conversation_messages(str(conv.id))
                result.append({
                    "id": str(conv.id),
                    "session_id": conv.session_id,
                    "created_at": conv.created_at.isoformat(),
                    "message_count": len(messages),
                    "last_message": messages[-1].content if messages else None
                })
            
            return result

# Global database instance
db_manager = DatabaseManager()