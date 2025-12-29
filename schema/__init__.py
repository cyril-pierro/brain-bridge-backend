from pydantic import BaseModel


class SuccessOut(BaseModel):
    message: str
