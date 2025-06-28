import re
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

def parse_natural_language_datetime(text: str) -> Optional[Dict[str, str]]:
    """Parse natural language datetime expressions"""
    try:
        text = text.lower().strip()
        now = datetime.now()
        
        # Handle relative dates
        if "tomorrow" in text:
            target_date = now + timedelta(days=1)
        elif "today" in text:
            target_date = now
        elif "next week" in text:
            target_date = now + timedelta(days=7)
        elif "next month" in text:
            target_date = now + relativedelta(months=1)
        elif any(day in text for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            target_date = _parse_day_of_week(text, now)
        else:
            # Try to parse absolute dates
            target_date = _parse_absolute_date(text, now)
        
        if not target_date:
            return None
        
        # Parse time
        time_match = _parse_time_expression(text)
        if time_match:
            target_date = target_date.replace(
                hour=time_match["hour"],
                minute=time_match["minute"],
                second=0,
                microsecond=0
            )
        else:
            # Default to 9 AM if no time specified
            target_date = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
        
        return {
            "date": target_date.isoformat(),
            "time": target_date.strftime("%H:%M")
        }
        
    except Exception as e:
        logger.error(f"Error parsing datetime: {str(e)}")
        return None

def _parse_day_of_week(text: str, reference_date: datetime) -> Optional[datetime]:
    """Parse day of week references like 'next Friday'"""
    days = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    
    for day_name, day_num in days.items():
        if day_name in text:
            days_ahead = day_num - reference_date.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            
            if "next" in text:
                days_ahead += 7
            
            return reference_date + timedelta(days=days_ahead)
    
    return None

def _parse_absolute_date(text: str, reference_date: datetime) -> Optional[datetime]:
    """Parse absolute date expressions"""
    try:
        # Look for date patterns
        date_patterns = [
            r"\d{1,2}/\d{1,2}/\d{4}",  # MM/DD/YYYY
            r"\d{1,2}-\d{1,2}-\d{4}",  # MM-DD-YYYY
            r"\d{4}-\d{1,2}-\d{1,2}",  # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return date_parser.parse(match.group())
        
        # Try dateutil parser for more flexible parsing
        # Extract potential date strings
        words = text.split()
        for i in range(len(words)):
            for j in range(i+1, min(i+4, len(words)+1)):
                candidate = " ".join(words[i:j])
                try:
                    parsed = date_parser.parse(candidate, fuzzy=True)
                    if parsed.date() >= reference_date.date():
                        return parsed
                except:
                    continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error parsing absolute date: {str(e)}")
        return None

def _parse_time_expression(text: str) -> Optional[Dict[str, int]]:
    """Parse time expressions from text"""
    try:
        # Common time patterns
        time_patterns = [
            (r"(\d{1,2}):(\d{2})\s*(am|pm)?", "exact"),
            (r"(\d{1,2})\s*(am|pm)", "hour_ampm"),
            (r"(\d{1,2})\s*o'?clock", "hour"),
        ]
        
        for pattern, pattern_type in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if pattern_type == "exact":
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    ampm = match.group(3)
                    
                    if ampm:
                        if ampm.lower() == "pm" and hour != 12:
                            hour += 12
                        elif ampm.lower() == "am" and hour == 12:
                            hour = 0
                    
                    return {"hour": hour, "minute": minute}
                
                elif pattern_type == "hour_ampm":
                    hour = int(match.group(1))
                    ampm = match.group(2)
                    
                    if ampm.lower() == "pm" and hour != 12:
                        hour += 12
                    elif ampm.lower() == "am" and hour == 12:
                        hour = 0
                    
                    return {"hour": hour, "minute": 0}
                
                elif pattern_type == "hour":
                    hour = int(match.group(1))
                    # Assume PM for afternoon hours if no AM/PM specified
                    if hour < 8:
                        hour += 12
                    
                    return {"hour": hour, "minute": 0}
        
        # Handle relative time expressions
        if "morning" in text:
            return {"hour": 9, "minute": 0}
        elif "afternoon" in text:
            return {"hour": 14, "minute": 0}
        elif "evening" in text:
            return {"hour": 18, "minute": 0}
        elif "noon" in text:
            return {"hour": 12, "minute": 0}
        
        return None
        
    except Exception as e:
        logger.error(f"Error parsing time: {str(e)}")
        return None

def extract_duration(text: str) -> Optional[int]:
    """Extract meeting duration from text"""
    try:
        # Look for duration patterns
        duration_patterns = [
            r"(\d+)\s*hours?",
            r"(\d+)\s*hrs?",
            r"(\d+)\s*minutes?",
            r"(\d+)\s*mins?",
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                duration = int(match.group(1))
                if "hour" in pattern or "hr" in pattern:
                    return duration * 60
                else:
                    return duration
        
        # Default durations based on meeting type
        if any(word in text.lower() for word in ["call", "quick", "brief"]):
            return 30
        elif any(word in text.lower() for word in ["meeting", "session"]):
            return 60
        elif any(word in text.lower() for word in ["workshop", "training"]):
            return 120
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting duration: {str(e)}")
        return None

def format_datetime_natural(iso_datetime: str) -> str:
    """Format ISO datetime string in natural language"""
    try:
        dt = datetime.fromisoformat(iso_datetime)
        
        # Get day of week and date
        day_name = dt.strftime("%A")
        date_str = dt.strftime("%B %d, %Y")
        
        # Format time
        time_str = dt.strftime("%I:%M %p").lstrip("0")
        
        # Check if it's today, tomorrow, or this week
        now = datetime.now()
        days_diff = (dt.date() - now.date()).days
        
        if days_diff == 0:
            return f"Today at {time_str}"
        elif days_diff == 1:
            return f"Tomorrow at {time_str}"
        elif days_diff < 7:
            return f"This {day_name} at {time_str}"
        else:
            return f"{day_name}, {date_str} at {time_str}"
        
    except Exception as e:
        logger.error(f"Error formatting datetime: {str(e)}")
        return iso_datetime

def validate_business_hours(dt: datetime) -> bool:
    """Check if datetime falls within business hours"""
    try:
        # Business hours: Monday-Friday, 9 AM - 5 PM
        if dt.weekday() >= 5:  # Weekend
            return False
        
        if dt.hour < 9 or dt.hour >= 17:  # Outside business hours
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating business hours: {str(e)}")
        return False

def get_next_business_day(dt: datetime) -> datetime:
    """Get the next business day after given datetime"""
    try:
        next_day = dt + timedelta(days=1)
        
        # Skip weekends
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        
        # Set to 9 AM
        next_day = next_day.replace(hour=9, minute=0, second=0, microsecond=0)
        
        return next_day
        
    except Exception as e:
        logger.error(f"Error getting next business day: {str(e)}")
        return dt
