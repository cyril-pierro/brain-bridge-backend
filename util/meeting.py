import datetime
import os.path
from typing import Optional, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.setting import settings


class MeetingUtils:
    """Utility class for Google Calendar and Google Meet integration."""

    # If modifying these scopes, delete the file token.json.
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    @staticmethod
    def _get_credentials():
        """Get valid Google API credentials."""
        creds = None

        # The file token.json stores the user's access and refresh tokens.
        token_path = settings.GOOGLE_CALENDAR_TOKEN_PATH
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, MeetingUtils.SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                credentials_path = settings.GOOGLE_CALENDAR_CREDENTIALS_PATH
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, MeetingUtils.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        return creds

    @staticmethod
    def create_google_meet_event(
        attendee_emails: List[str],
        start_datetime: datetime.datetime,
        summary: str = "Brain Bridge Tutoring Session",
        description: str = "Online tutoring session via Brain Bridge platform",
        duration_minutes: int = 60
    ) -> Optional[str]:
        """
        Creates a Google Calendar event with a Google Meet link.

        Args:
            attendee_emails: List of attendee email addresses
            start_datetime: When the meeting starts
            summary: Event title
            description: Event description
            duration_minutes: How long the meeting lasts

        Returns:
            Google Meet link if successful, None if failed
        """
        try:
            creds = MeetingUtils._get_credentials()
            service = build('calendar', 'v3', credentials=creds)

            # Calculate end time
            end_datetime = start_datetime + datetime.timedelta(minutes=duration_minutes)

            # Prepare attendees list
            attendees = [{'email': email} for email in attendee_emails]

            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': attendees,
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"brain-bridge-{int(start_datetime.timestamp())}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                },
                'reminders': {
                    'useDefault': True,
                },
            }

            # The 'conferenceDataVersion=1' parameter is REQUIRED to generate the Meet link
            event_result = service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendUpdates='all'  # This sends the email invitation automatically
            ).execute()

            meet_link = event_result.get('hangoutLink')
            if meet_link:
                print(f"Google Meet event created successfully! Link: {meet_link}")
                return meet_link
            else:
                print("Failed to generate Google Meet link")
                return None

        except HttpError as error:
            print(f"Google Calendar API error: {error}")
            return None
        except Exception as error:
            print(f"Unexpected error creating Google Meet event: {error}")
            return None

    @staticmethod
    def generate_zoom_meeting_link() -> str:
        """Generate a Zoom meeting link (placeholder for future implementation)."""
        # This would integrate with Zoom API in a real implementation
        return "https://zoom.us/j/placeholder"

    @staticmethod
    def get_meeting_link(
        booking_type: str,
        attendee_emails: List[str],
        start_datetime: datetime.datetime,
        duration_hours: int = 1
    ) -> Optional[str]:
        """
        Get appropriate meeting link based on booking type.

        Args:
            booking_type: Type of booking ('online' or 'in_person')
            attendee_emails: List of attendee email addresses
            start_datetime: When the meeting starts
            duration_hours: How long the meeting lasts in hours

        Returns:
            Meeting link if successful, None if failed
        """
        if booking_type.lower() == "online":
            return MeetingUtils.create_google_meet_event(
                attendee_emails=attendee_emails,
                start_datetime=start_datetime,
                duration_minutes=duration_hours * 60  # Convert hours to minutes
            )
        return None
