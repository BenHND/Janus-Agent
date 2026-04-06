"""
Calendar Context Provider - Provides calendar events and scheduling information
Part of TICKET-APP-001: Native Microsoft 365 / Outlook Connector

This module provides calendar context for better command understanding:
- Current and upcoming events
- Meeting information
- Calendar availability

Integration:
- Microsoft 365 (via O365 library)
- Future: macOS Calendar app via AppleScript, Google Calendar API
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CalendarProvider:
    """
    Calendar context provider

    Provides information about:
    - Current event (if in one)
    - Upcoming events (next few hours/days)
    - Calendar availability
    - Meeting participants

    Integration points:
    - Microsoft 365 (via O365 library) - PRIMARY
    - macOS Calendar app via AppleScript (future)
    - Google Calendar API (future)
    - iCal file parsing (future)
    """

    def __init__(
        self,
        look_ahead_hours: int = 24,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        username: Optional[str] = None,
    ):
        """
        Initialize calendar provider

        Args:
            look_ahead_hours: How many hours ahead to look for events
            client_id: Microsoft 365 Application (client) ID
            client_secret: Microsoft 365 client secret
            username: Microsoft 365 user email address
        """
        self.look_ahead_hours = look_ahead_hours
        self.enabled = False  # Disabled by default until integration is configured
        self.account = None
        self.calendar = None

        # Get credentials from parameters or environment variables
        self.client_id = client_id or os.environ.get("O365_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("O365_CLIENT_SECRET")
        self.username = username or os.environ.get("O365_USERNAME")

        # Try to initialize O365 connection if credentials are available
        if self.client_id and self.client_secret:
            self._init_o365_connection()

    def _init_o365_connection(self) -> bool:
        """
        Initialize O365 connection and authenticate if needed
        
        Returns:
            True if connection is established, False otherwise
        """
        try:
            from O365 import Account

            credentials = (self.client_id, self.client_secret)
            self.account = Account(
                credentials,
                username=self.username,
            )

            # Check if already authenticated
            if self.account.is_authenticated:
                self.calendar = self.account.schedule().get_default_calendar()
                logger.info("O365 calendar connection established (already authenticated)")
                return True
            else:
                logger.info(
                    "O365 calendar not authenticated. Call authenticate() or enable() with auth."
                )
                return False

        except ImportError:
            logger.warning(
                "O365 library not installed. Install with: pip install 'janus[office365]'"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize O365 connection: {e}")
            return False

    def authenticate(self, scopes: Optional[List[str]] = None) -> bool:
        """
        Authenticate with Microsoft 365

        Args:
            scopes: List of required scopes (default: Calendars.Read)

        Returns:
            True if authentication succeeded, False otherwise
        """
        if not self.account:
            logger.error("O365 account not initialized. Check credentials.")
            return False

        try:
            # Default scopes for calendar access
            if scopes is None:
                scopes = ['Calendars.Read']

            # Perform authentication flow
            if self.account.authenticate(requested_scopes=scopes):
                self.calendar = self.account.schedule().get_default_calendar()
                logger.info("O365 calendar authenticated successfully")
                return True
            else:
                logger.error("O365 authentication failed")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def get_current_event(self) -> Optional[Dict[str, Any]]:
        """
        Get current active event if user is in a meeting

        Returns:
            Event dictionary or None if no current event
        """
        if not self.enabled or not self.calendar:
            return None

        try:
            now = datetime.now()
            # Query events happening right now
            query = self.calendar.new_query('start').less_equal(now)
            query.chain('and').on_attribute('end').greater_equal(now)

            events = self.calendar.get_events(query=query, limit=1, include_recurring=True)

            for event in events:
                return self._format_event(event)

            return None

        except Exception as e:
            logger.error(f"Error getting current event: {e}")
            return None

    def get_upcoming_events(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get upcoming events within look_ahead_hours

        Args:
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries with title, start time, end time, and participants
        """
        if not self.enabled or not self.calendar:
            return []

        try:
            now = datetime.now()
            end_time = now + timedelta(hours=self.look_ahead_hours)

            # Query upcoming events
            query = self.calendar.new_query('start').greater_equal(now)
            query.chain('and').on_attribute('start').less_equal(end_time)

            events = self.calendar.get_events(
                query=query, limit=limit, order_by='start', include_recurring=True
            )

            formatted_events = []
            for event in events:
                formatted_events.append(self._format_event(event))

            return formatted_events

        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return []

    def _format_event(self, event) -> Dict[str, Any]:
        """
        Format an O365 event to a standard dictionary

        Args:
            event: O365 Event object

        Returns:
            Formatted event dictionary
        """
        try:
            # Extract attendees
            attendees = []
            if hasattr(event, 'attendees') and event.attendees:
                for attendee in event.attendees:
                    attendee_info = {
                        'name': attendee.name or attendee.address,
                        'email': attendee.address,
                    }
                    attendees.append(attendee_info)

            # Extract organizer
            organizer = None
            if hasattr(event, 'organizer') and event.organizer:
                organizer = {
                    'name': event.organizer.name or event.organizer.address,
                    'email': event.organizer.address,
                }

            return {
                'title': event.subject or 'No Title',
                'start': event.start.isoformat() if event.start else None,
                'end': event.end.isoformat() if event.end else None,
                'location': event.location.get('displayName', '') if event.location else '',
                'attendees': attendees,
                'organizer': organizer,
                'is_online_meeting': getattr(event, 'is_online_meeting', False),
                'body': event.body[:200] if event.body else '',  # First 200 chars
            }

        except Exception as e:
            logger.error(f"Error formatting event: {e}")
            return {
                'title': 'Unknown Event',
                'start': None,
                'end': None,
                'attendees': [],
            }

    def get_next_event(self) -> Optional[Dict[str, Any]]:
        """
        Get the next upcoming event

        Returns:
            Next event dictionary or None
        """
        events = self.get_upcoming_events(limit=1)
        return events[0] if events else None

    def is_available(self, start_time: datetime, end_time: datetime) -> bool:
        """
        Check if user is available during a time period

        Args:
            start_time: Start of time period
            end_time: End of time period

        Returns:
            True if available, False if busy
        """
        if not self.enabled or not self.calendar:
            return True  # Assume available if no calendar integration

        try:
            # TICKET-AUDIT-TODO-002: Implemented availability check
            # Query events that overlap with the requested time period
            # Overlap condition: event_start < end_time AND event_end > start_time
            # Using O365 query builder: .less() means < and .greater() means >
            query = self.calendar.new_query('start').less(end_time)
            query.chain('and').on_attribute('end').greater(start_time)
            
            # Get events in the time range
            events = self.calendar.get_events(query=query, limit=10, include_recurring=True)
            
            # Check if any events were found (indicating user is busy)
            for event in events:
                # User is not available if there's any event in this time period
                return False
            
            # No conflicts found - user is available
            return True
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            # On error, assume available to avoid blocking operations
            return True

    def get_context(self) -> Dict[str, Any]:
        """
        Get complete calendar context

        Returns:
            Dictionary with calendar information:
            - current_event: Current active event or None
            - next_event: Next upcoming event or None
            - upcoming_events: List of upcoming events
            - is_in_meeting: Boolean indicating if currently in a meeting
        """
        current_event = self.get_current_event()
        upcoming_events = self.get_upcoming_events()

        return {
            "current_event": current_event,
            "next_event": upcoming_events[0] if upcoming_events else None,
            "upcoming_events": upcoming_events,
            "is_in_meeting": current_event is not None,
            "enabled": self.enabled,
        }

    def enable(self):
        """Enable calendar provider"""
        # Verify calendar is available before enabling
        if self.calendar or self._init_o365_connection():
            self.enabled = True
            logger.info("Calendar provider enabled")
        else:
            logger.warning(
                "Calendar provider cannot be enabled - O365 not configured or authenticated"
            )

    def disable(self):
        """Disable calendar provider"""
        self.enabled = False
        logger.info("Calendar provider disabled")


# Example integration code for future use:
"""
# macOS Calendar via AppleScript:
def _get_macos_calendar_events(self):
    script = '''
    tell application "Calendar"
        set eventList to {}
        repeat with cal in calendars
            set calEvents to (every event of cal whose start date > (current date) and start date < ((current date) + 1 * days))
            repeat with evt in calEvents
                set end of eventList to {summary of evt, start date of evt, end date of evt}
            end repeat
        end repeat
        return eventList
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    # Parse and return events

# Google Calendar API:
def _get_google_calendar_events(self):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return events_result.get('items', [])
"""
