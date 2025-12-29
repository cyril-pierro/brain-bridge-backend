from pydantic import BaseModel
from datetime import datetime


class ContactFormIn(BaseModel):
    name: str
    email: str
    subject: str
    priority: str
    message: str


class ContactFormOut(BaseModel):
    ticket_id: str
    status: str
    estimated_response: str
    submitted_at: datetime


class SuccessOut(BaseModel):
    message: str
