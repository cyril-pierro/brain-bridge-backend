from schema.support import ContactFormIn, SuccessOut
from controller.support import SupportOp
from fastapi import APIRouter, BackgroundTasks

support_router = APIRouter(tags=["support"])


@support_router.post("/support/contact", response_model=SuccessOut)
def submit_contact_form(
    contact_data: ContactFormIn,
    background_tasks: BackgroundTasks
):
    """
    Submit a contact/support form
    - Creates a support ticket
    - Sends acknowledgement emails to both customer and support team
    - Returns success message with ticket information
    """
    return SupportOp.submit_contact_form(contact_data, background_tasks)
