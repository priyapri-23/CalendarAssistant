from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
from langgraph_agent import BookingAgent
from calendar_service import CalendarService
from database import db_manager
import uuid
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Booking Assistant API")

# Initialize services
calendar_service = CalendarService()
booking_agent = BookingAgent(calendar_service, db_manager)

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat messages and return AI responses"""
    try:
        # Generate conversation ID if not provided
        if not request.conversation_id:
            conversation = db_manager.create_conversation()
            conversation_id = str(conversation.id)
        else:
            conversation_id = request.conversation_id
            conversation = db_manager.get_conversation(conversation_id)
            if not conversation:
                conversation = db_manager.create_conversation()
                conversation_id = str(conversation.id)
        
        # Add user message to database
        db_manager.add_message(conversation_id, "user", request.message)
        
        # Get conversation history from database
        messages = db_manager.get_conversation_messages(conversation_id)
        history = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        # Process message with LangGraph agent  
        conv_state = {}
        if conversation and hasattr(conversation, 'state'):
            conv_state = conversation.state if conversation.state is not None else {}
        
        response = await booking_agent.process_message(
            message=request.message,
            conversation_state=conv_state,
            conversation_history=history,
            conversation_id=conversation_id
        )
        
        # Update conversation state in database
        db_manager.update_conversation_state(conversation_id, response.get("state", {}))
        
        # Add assistant response to database
        db_manager.add_message(conversation_id, "assistant", response["message"])
        
        return ChatResponse(
            response=response["message"],
            conversation_id=conversation_id
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/calendar/availability")
async def get_availability(start_date: str, end_date: str):
    """Get calendar availability for a date range"""
    try:
        availability = await calendar_service.get_availability(start_date, end_date)
        return {"availability": availability}
    except Exception as e:
        logger.error(f"Error getting availability: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get availability")

@app.post("/calendar/book")
async def book_appointment(
    title: str,
    start_time: str,
    end_time: str,
    description: str = ""
):
    """Book a calendar appointment"""
    try:
        event = await calendar_service.create_event(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description
        )
        return {"event": event, "status": "booked"}
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to book appointment")

@app.get("/conversations")
async def get_conversations(limit: int = 10):
    """Get recent conversation history"""
    try:
        conversations = db_manager.get_conversation_history(limit=limit)
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get conversations")

@app.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """Get messages for a specific conversation"""
    try:
        messages = db_manager.get_conversation_messages(conversation_id)
        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }
    except Exception as e:
        logger.error(f"Error getting conversation messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get messages")

@app.get("/bookings")
async def get_bookings(start_date: str = None, end_date: str = None):
    """Get booking records"""
    try:
        if start_date and end_date:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            bookings = db_manager.get_bookings_by_date_range(start_dt, end_dt)
        else:
            # Get recent bookings
            from database import Booking
            with db_manager.get_session() as session:
                bookings = session.query(Booking).filter(
                    Booking.status == "confirmed"
                ).order_by(Booking.start_time.desc()).limit(20).all()
        
        return {
            "bookings": [
                {
                    "id": str(booking.id),
                    "title": booking.title,
                    "description": booking.description,
                    "start_time": booking.start_time.isoformat(),
                    "end_time": booking.end_time.isoformat(),
                    "status": booking.status,
                    "created_at": booking.created_at.isoformat()
                }
                for booking in bookings
            ]
        }
    except Exception as e:
        logger.error(f"Error getting bookings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get bookings")

if __name__ == "__main__":
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
