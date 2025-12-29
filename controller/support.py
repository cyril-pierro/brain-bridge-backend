import logging
from datetime import datetime, timedelta
from schema.support import ContactFormIn, SuccessOut
from service.email import MailService
from fastapi import BackgroundTasks
import uuid
from config.setting import settings

logger = logging.getLogger(__name__)


class SupportOp:

    @staticmethod
    def submit_contact_form(contact_data: ContactFormIn,
                            background_tasks: BackgroundTasks) -> SuccessOut:
        """
        Submit a contact/support form and send acknowledgement emails
        """
        try:
            # Generate a unique ticket ID
            ticket_id = f"BB-{uuid.uuid4().hex[:8].upper()}"

            # Calculate estimated response time based on priority
            estimated_response = SupportOp._calculate_response_time(
                contact_data.priority)

            # Prepare email content for support team
            support_email_content = {
                "ticket_id": ticket_id,
                "customer_name": contact_data.name,
                "customer_email": contact_data.email,
                "subject": contact_data.subject,
                "priority": contact_data.priority,
                "message": contact_data.message,
                "submitted_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S UTC"),
                "estimated_response": estimated_response
            }

            # Prepare email content for customer acknowledgement
            customer_name = (
                contact_data.name.split()[0]
                if contact_data.name.split()
                else contact_data.name
            )
            customer_email_content = {
                "customer_name": customer_name,
                "ticket_id": ticket_id,
                "subject": contact_data.subject,
                "estimated_response": estimated_response,
                "submitted_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S UTC")
            }

            # Send email to support team (internal)
            background_tasks.add_task(
                MailService.send_email,
                email=settings.TEAM_SUPPORT_EMAIL,  # Support team email
                subject=("New Support Ticket: {ticket_id} - "
                         "{contact_data.subject}").format(
                    ticket_id=ticket_id,
                    contact_data=contact_data
                ),
                content=support_email_content,
                email_template="support_ticket.html"
            )

            # Send acknowledgement email to customer
            background_tasks.add_task(
                MailService.send_email,
                email=contact_data.email,
                subject=("Support Request Received - "
                         f"Ticket {ticket_id}"),
                content=customer_email_content,
                email_template="support_acknowledgement.html"
            )

            logger.info(
                f"Support ticket {ticket_id} submitted successfully for "
                f"{contact_data.email}"
            )

            return SuccessOut(
                message=("Support request submitted successfully. "
                         "We'll get back to you soon.")
            )

        except Exception as e:
            logger.error(f"Failed to submit support request: {e}")
            raise

    @staticmethod
    def _calculate_response_time(priority: str) -> str:
        """
        Calculate estimated response time based on priority level
        """
        now = datetime.now()

        if priority == "urgent":
            # Within 1 hour for urgent issues
            response_time = now + timedelta(hours=1)
            return (f"within 1 hour "
                    f"(by {response_time.strftime('%H:%M UTC today')})")
        elif priority == "high":
            # Within 4 hours for high priority
            response_time = now + timedelta(hours=4)
            return (f"within 4 hours "
                    f"(by {response_time.strftime('%H:%M UTC today')})")
        elif priority == "medium":
            # Within 24 hours for medium priority
            response_time = now + timedelta(hours=24)
            return (f"within 24 hours "
                    f"(by {response_time.strftime('%Y-%m-%d %H:%M UTC')})")
        else:  # low
            # Within 48 hours for low priority
            response_time = now + timedelta(hours=48)
            return (f"within 48 hours "
                    f"(by {response_time.strftime('%Y-%m-%d %H:%M UTC')})")
