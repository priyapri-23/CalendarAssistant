import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class CalendarService:
    """Google Calendar integration service"""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self):
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Calendar service with authentication"""
        try:
            creds = None
            
            # Try service account authentication first
            if os.path.exists('credentials.json'):
                try:
                    creds = service_account.Credentials.from_service_account_file(
                        'credentials.json', scopes=self.SCOPES
                    )
                    logger.info("Using service account authentication")
                except Exception as e:
                    logger.warning(f"Service account authentication failed: {str(e)}")
            
            # If no service account, try OAuth2 flow
            if not creds:
                # Check for existing OAuth token
                if os.path.exists('token.json'):
                    creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
                
                # If there are no (valid) credentials available, try OAuth flow
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    elif os.path.exists('client_secrets.json'):
                        # Run OAuth flow if client secrets available
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'client_secrets.json', self.SCOPES
                        )
                        creds = flow.run_local_server(port=0)
                    else:
                        logger.warning("No Google Calendar credentials found. Using mock service.")
                        logger.info("To use real Google Calendar:")
                        logger.info("1. Add 'credentials.json' (service account) OR")
                        logger.info("2. Add 'client_secrets.json' (OAuth2) to project root")
                        self.service = None
                        return
            
            if creds:
                # Save OAuth credentials for the next run (not needed for service account)
                if hasattr(creds, 'to_json') and not isinstance(creds, service_account.Credentials):
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                
                self.service = build('calendar', 'v3', credentials=creds)
                logger.info("Google Calendar service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar service: {str(e)}")
            self.service = None
    
    async def get_availability(self, start_date: str, end_date: str) -> List[Dict]:
        """Get available time slots between start_date and end_date"""
        try:
            if not self.service:
                # Mock response for demo purposes
                return self._get_mock_availability(start_date, end_date)
            
            # Convert string dates to RFC3339 format
            start_datetime = datetime.fromisoformat(start_date).isoformat() + 'Z'
            end_datetime = datetime.fromisoformat(end_date).isoformat() + 'Z'
            
            # Get events from primary calendar
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_datetime,
                timeMax=end_datetime,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Calculate available slots
            available_slots = self._calculate_available_slots(
                events, start_date, end_date
            )
            
            return available_slots
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {str(e)}")
            return self._get_mock_availability(start_date, end_date)
        except Exception as e:
            logger.error(f"Error getting availability: {str(e)}")
            return []
    
    async def create_event(
        self, 
        title: str, 
        start_time: str, 
        end_time: str, 
        description: str = ""
    ) -> Dict:
        """Create a new calendar event"""
        try:
            if not self.service:
                # Mock response for demo purposes
                return self._create_mock_event(title, start_time, end_time, description)
            
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': datetime.fromisoformat(start_time).isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': datetime.fromisoformat(end_time).isoformat(),
                    'timeZone': 'UTC',
                },
            }
            
            created_event = self.service.events().insert(
                calendarId='primary', 
                body=event
            ).execute()
            
            return {
                'id': created_event['id'],
                'title': created_event['summary'],
                'start_time': created_event['start']['dateTime'],
                'end_time': created_event['end']['dateTime'],
                'html_link': created_event['htmlLink']
            }
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {str(e)}")
            raise Exception(f"Failed to create calendar event: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            raise Exception(f"Failed to create calendar event: {str(e)}")
    
    def _get_mock_availability(self, start_date: str, end_date: str) -> List[Dict]:
        """Generate mock availability for demo purposes"""
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            
            available_slots = []
            current = start
            
            while current < end:
                # Skip weekends
                if current.weekday() < 5:  # Monday = 0, Friday = 4
                    # Add morning slot (9 AM - 12 PM)
                    morning_start = current.replace(hour=9, minute=0, second=0, microsecond=0)
                    morning_end = current.replace(hour=12, minute=0, second=0, microsecond=0)
                    
                    if morning_start >= start and morning_end <= end:
                        available_slots.append({
                            'start': morning_start.isoformat(),
                            'end': morning_end.isoformat(),
                            'type': 'available'
                        })
                    
                    # Add afternoon slot (2 PM - 5 PM)
                    afternoon_start = current.replace(hour=14, minute=0, second=0, microsecond=0)
                    afternoon_end = current.replace(hour=17, minute=0, second=0, microsecond=0)
                    
                    if afternoon_start >= start and afternoon_end <= end:
                        available_slots.append({
                            'start': afternoon_start.isoformat(),
                            'end': afternoon_end.isoformat(),
                            'type': 'available'
                        })
                
                current += timedelta(days=1)
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Error generating mock availability: {str(e)}")
            return []
    
    def _create_mock_event(self, title: str, start_time: str, end_time: str, description: str) -> Dict:
        """Create a mock event response for demo purposes"""
        import uuid
        return {
            'id': str(uuid.uuid4()),
            'title': title,
            'start_time': start_time,
            'end_time': end_time,
            'description': description,
            'html_link': f"https://calendar.google.com/calendar/event?eid={uuid.uuid4()}"
        }
    
    def _calculate_available_slots(
        self, 
        events: List[Dict], 
        start_date: str, 
        end_date: str
    ) -> List[Dict]:
        """Calculate available time slots based on existing events"""
        try:
            # For simplicity, return business hours that don't conflict with events
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            
            # Extract busy times from events
            busy_times = []
            for event in events:
                if 'start' in event and 'end' in event:
                    event_start = datetime.fromisoformat(
                        event['start'].get('dateTime', event['start'].get('date'))
                    )
                    event_end = datetime.fromisoformat(
                        event['end'].get('dateTime', event['end'].get('date'))
                    )
                    busy_times.append((event_start, event_end))
            
            # Generate available slots (simplified logic)
            available_slots = []
            current = start
            
            while current < end:
                if current.weekday() < 5:  # Weekdays only
                    # Check morning slot
                    morning_start = current.replace(hour=9, minute=0, second=0, microsecond=0)
                    morning_end = current.replace(hour=12, minute=0, second=0, microsecond=0)
                    
                    if not self._is_time_busy(morning_start, morning_end, busy_times):
                        available_slots.append({
                            'start': morning_start.isoformat(),
                            'end': morning_end.isoformat(),
                            'type': 'available'
                        })
                    
                    # Check afternoon slot
                    afternoon_start = current.replace(hour=14, minute=0, second=0, microsecond=0)
                    afternoon_end = current.replace(hour=17, minute=0, second=0, microsecond=0)
                    
                    if not self._is_time_busy(afternoon_start, afternoon_end, busy_times):
                        available_slots.append({
                            'start': afternoon_start.isoformat(),
                            'end': afternoon_end.isoformat(),
                            'type': 'available'
                        })
                
                current += timedelta(days=1)
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Error calculating available slots: {str(e)}")
            return []
    
    def _is_time_busy(self, start: datetime, end: datetime, busy_times: List[tuple]) -> bool:
        """Check if a time slot conflicts with busy times"""
        for busy_start, busy_end in busy_times:
            if (start < busy_end and end > busy_start):
                return True
        return False
