import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel
import re
from utils import parse_natural_language_datetime, extract_duration, format_datetime_natural
from openai import OpenAI

logger = logging.getLogger(__name__)

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "demo_key")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

class ConversationState(BaseModel):
    """State model for conversation flow"""
    intent: Optional[str] = None
    requested_date: Optional[str] = None
    requested_time: Optional[str] = None
    duration: Optional[int] = 60  # Default 60 minutes
    meeting_title: Optional[str] = None
    meeting_description: Optional[str] = None
    available_slots: List[Dict] = []
    confirmed_slot: Optional[Dict] = None
    step: str = "greeting"
    user_message: str = ""
    last_response: str = ""

class BookingAgent:
    """LangGraph-based conversational booking agent"""
    
    def __init__(self, calendar_service, db_manager=None):
        self.calendar_service = calendar_service
        self.db_manager = db_manager
        self.memory = MemorySaver()
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph conversation flow"""
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("understand_intent", self._understand_intent)
        workflow.add_node("parse_datetime", self._parse_datetime)
        workflow.add_node("check_availability", self._check_availability)
        workflow.add_node("suggest_slots", self._suggest_slots)
        workflow.add_node("confirm_booking", self._confirm_booking)
        workflow.add_node("book_appointment", self._book_appointment)
        workflow.add_node("handle_error", self._handle_error)
        
        # Set entry point
        workflow.set_entry_point("understand_intent")
        
        # Add edges
        workflow.add_conditional_edges(
            "understand_intent",
            self._route_intent,
            {
                "parse_datetime": "parse_datetime",
                "clarify": END,
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "parse_datetime",
            self._route_datetime,
            {
                "check_availability": "check_availability",
                "clarify_time": END,
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "check_availability",
            self._route_availability,
            {
                "suggest_slots": "suggest_slots",
                "no_availability": END,
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "suggest_slots",
            self._route_suggestion,
            {
                "confirm_booking": "confirm_booking",
                "alternative": "check_availability",
                "clarify": END
            }
        )
        
        workflow.add_conditional_edges(
            "confirm_booking",
            self._route_confirmation,
            {
                "book_appointment": "book_appointment",
                "modify": "parse_datetime",
                "cancel": END
            }
        )
        
        workflow.add_edge("book_appointment", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile(checkpointer=self.memory)
    
    async def process_message(
        self, 
        message: str, 
        conversation_state: Dict, 
        conversation_history: List[Dict],
        conversation_id: str = None
    ) -> Dict[str, Any]:
        """Process a user message and return AI response"""
        try:
            # Create state from conversation
            state = ConversationState(
                user_message=message,
                **conversation_state
            )
            
            # Store conversation ID for database operations
            self._current_conversation_id = conversation_id
            
            # Run the graph
            result = await self.graph.ainvoke(
                state,
                {"configurable": {"thread_id": conversation_id or "default"}}
            )
            
            return {
                "message": result.get("last_response", "I'm sorry, I couldn't process that request."),
                "state": {k: v for k, v in result.items() if k != "last_response"}
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "message": "I apologize, but I'm experiencing technical difficulties. Please try again.",
                "state": conversation_state
            }
    
    async def _understand_intent(self, state: ConversationState) -> ConversationState:
        """Understand user intent using OpenAI"""
        try:
            prompt = f"""
            Analyze this user message for booking intent: "{state.user_message}"
            
            Determine the intent and extract key information. Respond in JSON format:
            {{
                "intent": "booking|inquiry|modification|cancellation|other",
                "has_date": true|false,
                "has_time": true|false,
                "urgency": "low|medium|high",
                "meeting_type": "meeting|call|appointment|other"
            }}
            """
            
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
            else:
                result = {"intent": "other"}
            state.intent = result.get("intent", "other")
            
            if state.intent == "booking":
                state.step = "parse_datetime"
            else:
                state.last_response = self._generate_clarification_response(state.user_message)
                state.step = "clarify"
            
            return state
            
        except Exception as e:
            logger.error(f"Error understanding intent: {str(e)}")
            state.step = "error"
            return state
    
    async def _parse_datetime(self, state: ConversationState) -> ConversationState:
        """Parse date/time from user message"""
        try:
            # Use utility function to parse natural language datetime
            parsed_datetime = parse_natural_language_datetime(state.user_message)
            
            if parsed_datetime:
                state.requested_date = parsed_datetime["date"]
                state.requested_time = parsed_datetime["time"]
                state.duration = extract_duration(state.user_message) or 60
                state.step = "check_availability"
            else:
                state.last_response = (
                    "I need more specific information about when you'd like to schedule. "
                    "Could you please provide a date and time? For example: "
                    "'tomorrow at 2 PM' or 'next Friday morning'."
                )
                state.step = "clarify_time"
            
            return state
            
        except Exception as e:
            logger.error(f"Error parsing datetime: {str(e)}")
            state.step = "error"
            return state
    
    async def _check_availability(self, state: ConversationState) -> ConversationState:
        """Check calendar availability"""
        try:
            if not state.requested_date:
                state.step = "error"
                return state
            
            # Calculate search range
            start_date = state.requested_date
            end_date = (datetime.fromisoformat(start_date) + timedelta(days=7)).isoformat()
            
            # Get availability from calendar service
            availability = await self.calendar_service.get_availability(start_date, end_date)
            state.available_slots = availability
            
            if availability:
                state.step = "suggest_slots"
            else:
                state.last_response = (
                    f"I don't see any available slots around {format_datetime_natural(state.requested_date)}. "
                    "Would you like me to check a different time period?"
                )
                state.step = "no_availability"
            
            return state
            
        except Exception as e:
            logger.error(f"Error checking availability: {str(e)}")
            state.step = "error"
            return state
    
    async def _suggest_slots(self, state: ConversationState) -> ConversationState:
        """Suggest available time slots to user"""
        try:
            if not state.available_slots:
                state.step = "no_availability"
                return state
            
            # Find best matching slots
            best_slots = self._find_best_slots(state)
            
            if best_slots:
                slots_text = self._format_slots_for_user(best_slots[:3])  # Show top 3
                state.last_response = (
                    f"I found some available times for you:\n\n{slots_text}\n\n"
                    "Which time works best for you? Just let me know the number or "
                    "describe your preference."
                )
                state.step = "confirm_booking"
            else:
                state.last_response = (
                    "I couldn't find any slots that match your preferred time. "
                    "Would you like me to suggest alternative times?"
                )
                state.step = "alternative"
            
            return state
            
        except Exception as e:
            logger.error(f"Error suggesting slots: {str(e)}")
            state.step = "error"
            return state
    
    async def _confirm_booking(self, state: ConversationState) -> ConversationState:
        """Handle booking confirmation"""
        try:
            user_response = state.user_message.lower()
            
            # Parse user selection
            if any(word in user_response for word in ['yes', 'confirm', 'book', 'schedule']):
                # User confirmed, proceed to booking
                if state.available_slots:
                    state.confirmed_slot = state.available_slots[0]  # Use first suggested slot
                    state.step = "book_appointment"
                else:
                    state.step = "error"
            elif any(word in user_response for word in ['no', 'different', 'other', 'change']):
                # User wants different time
                state.last_response = (
                    "No problem! Please let me know what time you'd prefer, "
                    "and I'll check availability."
                )
                state.step = "modify"
            elif re.search(r'\d+', user_response):
                # User selected a numbered option
                try:
                    match = re.search(r'\d+', user_response)
                    if match:
                        selection = int(match.group()) - 1
                    else:
                        raise ValueError("No number found")
                    if 0 <= selection < len(state.available_slots):
                        state.confirmed_slot = state.available_slots[selection]
                        state.step = "book_appointment"
                    else:
                        state.last_response = "Please select a valid option number."
                        state.step = "clarify"
                except ValueError:
                    state.step = "clarify"
            else:
                state.last_response = (
                    "I didn't quite understand your preference. Could you please "
                    "confirm one of the suggested times or let me know what you'd prefer?"
                )
                state.step = "clarify"
            
            return state
            
        except Exception as e:
            logger.error(f"Error confirming booking: {str(e)}")
            state.step = "error"
            return state
    
    async def _book_appointment(self, state: ConversationState) -> ConversationState:
        """Book the confirmed appointment"""
        try:
            if not state.confirmed_slot:
                state.step = "error"
                return state
            
            # Generate meeting title if not provided
            if not state.meeting_title:
                state.meeting_title = "Meeting"
            
            # Calculate end time
            start_time = state.confirmed_slot["start"]
            duration_minutes = state.duration or 60
            end_time = (
                datetime.fromisoformat(start_time) + 
                timedelta(minutes=duration_minutes)
            ).isoformat()
            
            # Book the appointment
            event = await self.calendar_service.create_event(
                title=state.meeting_title,
                start_time=start_time,
                end_time=end_time,
                description=state.meeting_description or "Scheduled via AI Assistant"
            )
            
            # Save booking to database if available
            if self.db_manager and hasattr(self, '_current_conversation_id'):
                try:
                    booking = self.db_manager.create_booking(
                        conversation_id=self._current_conversation_id,
                        title=state.meeting_title,
                        start_time=datetime.fromisoformat(start_time),
                        end_time=datetime.fromisoformat(end_time),
                        description=state.meeting_description,
                        calendar_event_id=event.get('id'),
                        extra_data={
                            'duration': duration_minutes,
                            'agent_version': 'v1.0'
                        }
                    )
                    logger.info(f"Booking saved to database: {booking.id}")
                except Exception as e:
                    logger.error(f"Failed to save booking to database: {str(e)}")
            
            formatted_time = format_datetime_natural(start_time)
            state.last_response = (
                f"✅ Perfect! I've booked your {state.meeting_title.lower()} for "
                f"{formatted_time}. You should receive a calendar invitation shortly.\n\n"
                f"Event details:\n"
                f"• Title: {state.meeting_title}\n"
                f"• Date & Time: {formatted_time}\n"
                f"• Duration: {duration_minutes} minutes\n\n"
                "Is there anything else I can help you with?"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Error booking appointment: {str(e)}")
            state.last_response = (
                "I apologize, but I encountered an error while booking your appointment. "
                "Please try again or contact support if the issue persists."
            )
            state.step = "error"
            return state
    
    async def _handle_error(self, state: ConversationState) -> ConversationState:
        """Handle errors gracefully"""
        state.last_response = (
            "I apologize, but I encountered an issue processing your request. "
            "Could you please try rephrasing your booking request? For example: "
            "'I need to schedule a meeting for tomorrow at 2 PM'."
        )
        return state
    
    def _route_intent(self, state: ConversationState) -> str:
        """Route based on understood intent"""
        if state.step == "error":
            return "error"
        elif state.intent == "booking":
            return "parse_datetime"
        else:
            return "clarify"
    
    def _route_datetime(self, state: ConversationState) -> str:
        """Route based on datetime parsing results"""
        if state.step == "error":
            return "error"
        elif state.step == "check_availability":
            return "check_availability"
        else:
            return "clarify_time"
    
    def _route_availability(self, state: ConversationState) -> str:
        """Route based on availability check results"""
        if state.step == "error":
            return "error"
        elif state.step == "suggest_slots":
            return "suggest_slots"
        else:
            return "no_availability"
    
    def _route_suggestion(self, state: ConversationState) -> str:
        """Route based on slot suggestion results"""
        if state.step == "confirm_booking":
            return "confirm_booking"
        elif state.step == "alternative":
            return "alternative"
        else:
            return "clarify"
    
    def _route_confirmation(self, state: ConversationState) -> str:
        """Route based on confirmation response"""
        if state.step == "book_appointment":
            return "book_appointment"
        elif state.step == "modify":
            return "modify"
        else:
            return "cancel"
    
    def _generate_clarification_response(self, message: str) -> str:
        """Generate appropriate clarification response"""
        return (
            "I'd be happy to help you schedule an appointment! "
            "Please let me know when you'd like to book a meeting. "
            "For example, you could say: 'I need a meeting tomorrow at 2 PM' "
            "or 'Do you have any time available this Friday afternoon?'"
        )
    
    def _find_best_slots(self, state: ConversationState) -> List[Dict]:
        """Find the best matching slots based on user preferences"""
        if not state.available_slots:
            return []
        
        # For now, return available slots sorted by start time
        # In a more sophisticated implementation, we could score slots
        # based on user preferences, time of day, etc.
        return sorted(
            state.available_slots,
            key=lambda x: x["start"]
        )
    
    def _format_slots_for_user(self, slots: List[Dict]) -> str:
        """Format available slots for user display"""
        formatted_slots = []
        for i, slot in enumerate(slots, 1):
            start_time = format_datetime_natural(slot["start"])
            formatted_slots.append(f"{i}. {start_time}")
        
        return "\n".join(formatted_slots)
