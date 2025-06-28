# AI Booking Assistant

## Overview

This is a conversational AI booking assistant that allows users to schedule appointments using natural language. The system combines a Streamlit frontend with a FastAPI backend, utilizing LangGraph for conversation flow management and Google Calendar integration for appointment scheduling.

## System Architecture

The application follows a client-server architecture with three main layers:

1. **Frontend (Streamlit)**: Web-based user interface for chat interactions
2. **Backend (FastAPI)**: REST API server handling conversation logic and business operations
3. **External Services**: Google Calendar API for appointment management

The system uses LangGraph to manage conversational state and flow, allowing for natural language processing of scheduling requests.

## Key Components

### Frontend (`app.py`)
- **Technology**: Streamlit web framework
- **Purpose**: Provides chat interface for user interactions
- **Key Features**: 
  - Auto-starts backend service if not running
  - Real-time chat interface
  - Health monitoring of backend service

### Backend (`backend.py`)
- **Technology**: FastAPI framework
- **Purpose**: Handles API requests and conversation management
- **Key Features**:
  - RESTful API endpoints
  - Conversation state management
  - Integration with AI agent and calendar services

### AI Agent (`langgraph_agent.py`)
- **Technology**: LangGraph for conversation flow, OpenAI GPT-4o for natural language processing
- **Purpose**: Manages booking conversation flow and intent understanding
- **Key Features**:
  - State-based conversation management
  - Natural language intent recognition
  - Multi-step booking process

### Calendar Service (`calendar_service.py`)
- **Technology**: Google Calendar API
- **Purpose**: Handles calendar operations and availability checking
- **Key Features**:
  - OAuth2 authentication with Google
  - Calendar availability checking
  - Appointment creation and management
  - Fallback to mock service for development

### Utilities (`utils.py`)
- **Purpose**: Natural language datetime parsing and formatting
- **Key Features**:
  - Relative date parsing (tomorrow, next week, etc.)
  - Time expression parsing
  - Duration extraction from text

## Data Flow

1. User enters natural language booking request in Streamlit frontend
2. Frontend sends request to FastAPI backend via `/chat` endpoint
3. Backend routes request to LangGraph booking agent
4. Agent processes message through conversation state machine:
   - Understands user intent
   - Parses datetime information
   - Checks calendar availability
   - Suggests available slots
   - Confirms booking
5. Calendar service interacts with Google Calendar API
6. Response flows back through the chain to user

## External Dependencies

- **OpenAI API**: For natural language processing (GPT-4o model)
- **Google Calendar API**: For calendar integration and appointment management
- **Core Libraries**:
  - FastAPI for backend API
  - Streamlit for frontend
  - LangGraph for conversation flow
  - Pydantic for data validation
  - dateutil for datetime parsing

## Deployment Strategy

The application uses a hybrid deployment approach:
- Frontend and backend run as separate processes
- Backend auto-starts when frontend initializes
- Services communicate via HTTP on localhost
- Designed for single-machine deployment with potential for containerization

**Authentication**: Uses OAuth2 flow for Google Calendar with token caching

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

✓ Added comprehensive Google Calendar integration with dual authentication support (service account + OAuth2)
✓ Enhanced calendar service with robust error handling and fallback to demonstration mode
✓ Created detailed setup guide (GOOGLE_CALENDAR_SETUP.md) for real calendar integration
✓ Implemented security best practices with .gitignore for credential files
✓ Fixed LangGraph type compatibility issues for stable conversation flow
✓ Integrated PostgreSQL database for persistent storage of conversations, messages, and bookings
✓ Added new API endpoints for viewing conversation history and booking records
✓ Enhanced Streamlit interface with data visualization sidebar for conversations and bookings

## Changelog

- June 28, 2025: Initial setup with full conversational AI booking system
- June 28, 2025: Added Google Calendar integration with setup documentation
