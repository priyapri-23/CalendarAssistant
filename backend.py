from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
from langgraph_agent import BookingAgent
from calendar_service import CalendarService
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Booking Assistant API")

# Initialize services
calendar_service = CalendarService()
booking_agent = BookingAgent(calendar_service)

# Store conversation states
conversations = {}

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = None

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
            request.conversation_id = str(uuid.uuid4())
        
        # Get or create conversation state
        if request.conversation_id not in conversations:
            conversations[request.conversation_id] = {
                "state": {},
                "history": []
            }
        
        conversation = conversations[request.conversation_id]
        
        # Add user message to history
        conversation["history"].append({
            "role": "user",
            "content": request.message
        })
        
        # Process message with LangGraph agent
        response = await booking_agent.process_message(
            message=request.message,
            conversation_state=conversation["state"],
            conversation_history=conversation["history"]
        )
        
        # Update conversation state
        conversation["state"] = response.get("state", {})
        conversation["history"].append({
            "role": "assistant",
            "content": response["message"]
        })
        
        return ChatResponse(
            response=response["message"],
            conversation_id=request.conversation_id
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

if __name__ == "__main__":
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
