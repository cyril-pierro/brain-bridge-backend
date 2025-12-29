from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from jinja2 import Environment, FileSystemLoader
from pydantic import EmailStr
from datetime import datetime

from config.setting import settings


file_loader = FileSystemLoader(searchpath="template/")
env = Environment(loader=file_loader, auto_reload=True, autoescape=True)


class MailService:
    mail_config = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=str(settings.MAIL_PASSWORD).strip(),
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        USE_CREDENTIALS=settings.USE_CREDENTIALS,
        VALIDATE_CERTS=settings.VALIDATE_CERTS,
        TEMPLATE_FOLDER="template",
        MAIL_DEBUG=settings.MAIL_DEBUG,
    )

    @classmethod
    async def send_email(
        cls,
        email: EmailStr,
        subject: str,
        content: dict[str, str] = None,
        email_template: str = "suspicious_email.html",
    ):
        # Prepare content with system-generated values
        email_content = content or {}
        email_content['current_year'] = str(datetime.now().year)

        template = env.get_template(email_template)
        html = template.render(**email_content)
        try:
            message = MessageSchema(
                subject=subject, recipients=[
                    email], body=html, subtype=MessageType.html
            )

            fm = FastMail(cls.mail_config)
            await fm.send_message(message, template_name=email_template)
            print("Email sent")
            return True
        except ConnectionErrors as e:
            raise ConnectionErrors(e) from e
        except Exception as e:
            print(f"Failed to send message -> {str(e)}")
